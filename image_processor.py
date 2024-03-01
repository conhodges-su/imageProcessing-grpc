import abc
import cv2
import grpc
import image_pb2
import image_pb2_grpc
import uuid
import math
import os



# module constants used for performing command comparisons
FLIP = "flip"
ROTATE = "rotate"
LEFT = "left"
RIGHT = "right"
RIGHT_DEGREES = -90
LEFT_DEGREES = 90
GREYSCALE = "greyscale"
RESIZE = "resize"
THUMBNAIL = "thumbnail"
HORIZONTAL = "horizontal"
VERTICAL = "vertical"
THUMBNAIL_SIZE = 200 
MAXIMUM_PERCENT = 500
MINIMUM_PERCENT = -95
ERROR_400 = 400
HORIZ_FLIP = 1
VERT_FLIP = 0
DEGREES_MODULO = 360
CHUNK_SIZE = 64 * 1024 # 64 KiB
NEW_FILE_INCOMING = "NEW_FILE_INCOMING"

def uuid_generator(filetype):
    return str(str(f"{uuid.uuid4()}.{filetype}"))

class IImageProcessor(abc.ABC):
    @abc.abstractmethod
    def process_image(self):
        pass

class ImageProcessor(IImageProcessor):
    def __init__(self, img, string_cmds, img_type):
        self._img = img
        self._cmds = self._cmds_to_list(string_cmds)
        self._img_type = img_type
        self._new_img = None
        self._new_thumbnail = None
        self._errs = None 

    
    def process_image(self):
        # iterate over all commands
        errs = []
        img = cv2.imread(self._img)
        updated_imgs = dict(img=img,
                            img_name=None,
                            thumbnail=None,
                            thumbnail_name=None)
        for cmd in self._cmds:
            updated_imgs, errs = self._execute_cmd(updated_imgs, cmd, errs)
        self._errs = errs

        # write img to file to use to stream back to client    
        updated_imgs['img_name'] = uuid_generator(self._img_type)
        cv2.imwrite(updated_imgs['img_name'], updated_imgs['img'])
        self._new_img = updated_imgs['img_name']

        # write thumbnail to file, only if present
        if updated_imgs['thumbnail'] is not None:
            updated_imgs['thumbnail_name'] = uuid_generator(self._img_type)
            cv2.imwrite(updated_imgs['thumbnail_name'], updated_imgs['thumbnail'])
            self._new_thumbnail = updated_imgs['thumbnail_name']
        
        return updated_imgs, errs


    def _cmds_to_list(self, string_cmds):
        rows = string_cmds.split("\n")
        new_list = []
        for row in rows:
            updated = row.split()
            new_list.append(updated)
        return new_list
    

    def _execute_cmd(self, imgs, cmd, errs):
        if cmd[0] == FLIP:
            return self._flip_image(imgs, cmd, errs)
        elif cmd[0] == ROTATE:
            return self._rotate_image(imgs, cmd, errs)
        elif cmd[0] == GREYSCALE:
            return self._greyscale_image(imgs, errs)
        elif cmd[0] == RESIZE:
            return self._resize_image(imgs, cmd, errs)
        elif cmd[0] == THUMBNAIL:
            new_cmd = (THUMBNAIL, THUMBNAIL_SIZE, THUMBNAIL_SIZE)
            return self._thumbnail_image(imgs, new_cmd, errs)
        else:
            errs.append((ERROR_400, f"invalid function {cmd}"))
            return imgs, errs
        
    
    def _flip_image(self, imgs, cmd, errs):
        """
        Flips the image over the horizontal or vertical axis
        """

        # get commands from the paramter
        flip_type = cmd[1]
        try:
            if flip_type == HORIZONTAL:
                flip_cmd = HORIZ_FLIP
            elif flip_type == VERT_FLIP:
                flip_cmd = VERT_FLIP
            else:
                raise TypeError(f"{flip_type} invalid command. Usage: <horizontal/vertical>")
            imgs['img'] = cv2.flip(imgs['img'], flip_cmd)
            return imgs, errs
        except TypeError as te:
            errs.append((ERROR_400, te))
            return imgs, errs


    def _rotate_image(self, imgs, cmd, errs):
        """
        Rotates an image N degrees. The provided commands can be done with a 
        word (left for counterclockwise 90 degrees, right for clockwise 90
        degrees) or with an integer between -10000 and 10000
        """
        # set degrees to the cmd argument, then test if string command followed 
        # by casting as an int
        degrees = cmd[1]
        try:
            if degrees == LEFT:
                rotation = LEFT_DEGREES
            elif degrees == RIGHT:
                rotation = RIGHT_DEGREES
            else:
                try:
                    # strip out plus sign if provided
                    if cmd[1].startswith("+"):
                        cmd[1] = cmd[1][1:]
                    degrees = int(cmd[1])
                    rotation = degrees % DEGREES_MODULO if degrees >= 0 else (-1 * ((-1 * degrees) % DEGREES_MODULO))
                    rotation *= -1
                except ValueError as ve:
                    errs.append((ERROR_400, f"'{cmd[1]}' is invalid rotation command. Only integers allowed"))
                    return imgs, errs
        except ValueError as ve:
            print(f"Error {ve}: could not read degree rotation, returning original")
            errs.append((ERROR_400, "Error: invalid parameter for rotation"))
            return imgs, errs
        else:
            """
            Rotates an image (angle in degrees) and expands image to avoid cropping
            https://stackoverflow.com/questions/22041699/rotate-an-image-without-cropping-in-opencv-in-c/33564950#33564950
            """
            height, width = imgs['img'].shape[:2]
            image_center = (width / 2, height / 2)

            rotation_mat = cv2.getRotationMatrix2D(image_center, rotation, 1)

            radians = math.radians(rotation)
            sin = math.sin(radians)
            cos = math.cos(radians)
            bound_w = int((height * abs(sin)) + (width * abs(cos)))
            bound_h = int((height * abs(cos)) + (width * abs(sin)))

            rotation_mat[0, 2] += ((bound_w / 2) - image_center[0])
            rotation_mat[1, 2] += ((bound_h / 2) - image_center[1])

            rotated_mat = cv2.warpAffine(imgs['img'], rotation_mat, (bound_w, bound_h))
            imgs['img'] = rotated_mat

            return imgs, errs


    def _greyscale_image(self, imgs, errs):
        """
        converts image to greyscale
        """
        # Use the cvtColor() function to grayscale the image 
        # ref: https://www.geeksforgeeks.org/python-grayscaling-of-images-using-opencv/
        imgs['img'] = cv2.cvtColor(imgs['img'], cv2.COLOR_BGR2GRAY)
        return imgs, errs    


    def _resize_image(self, imgs, cmd, errs):
        """
        Resizes an image according to a % scalaing factor provided
        """

        # get commands from the paramter
        try:
            # new_size = (width, height), check dimensions
            percent_change = int(cmd[1])
            self._check_dimension(percent_change)
            print(f"Change: {percent_change}")
            factor = self._convert_to_factor(percent_change)
            print(f"Factor: {factor}")
            imgs['img'] = cv2.resize(imgs['img'], None, fx=factor, fy=factor, interpolation=cv2.INTER_LINEAR)
        except ValueError as ve:
            print(f"Error {ve}")
            errs.append((ERROR_400, ve))
            return imgs, errs
        except Exception as e:
            print(f"Error encountered, stopping image conversion")
            errs.append((ERROR_400, e))
            return imgs, errs
        else:
            return imgs, errs
    

    def _thumbnail_image(self, imgs, cmd, errs):
        # TODO: only send the first one
         # get commands from the paramter
        try:
            self._check_thumbnail_prescence(imgs)
            # new_size = (width, height), check dimensions
            new_size = (int(cmd[1]), int(cmd[2]))
            imgs['thumbnail'] = cv2.resize(imgs['img'], new_size)
        except ValueError as ve:
            print(f"Error {ve}")
            errs.append((ERROR_400, ve))
            return imgs, errs
        except Exception as e:
            print(f"Error encountered, stopping image conversion")
            errs.append((ERROR_400, e))
            return imgs, errs
        else:
            return imgs, errs
    
    def _check_dimension(self, percent):
        if percent > MAXIMUM_PERCENT:
            raise ValueError("Cannot resize/scale by more than 500%")
        elif percent < MINIMUM_PERCENT:
            raise ValueError("Cannot resize/scale by less than -95%")
    

    def _check_thumbnail_prescence(self, imgs):
        if imgs['thumbnail'] is not None:
            raise Exception("'thumbnail' call can only be called one time")
    

    def _convert_to_factor(self, percent):
        if percent >= 0:
            return (percent / 100) + 1
        if percent < 0:
            return 1 - (abs(percent) / 100)

    
    def transmit_img(self):
        """
        ref: https://stackoverflow.com/questions/4566498/what-is-the-idiomatic-way-to-iterate-over-a-binary-file
        """
        print("transferring back")
        
        # prepare error string
        err_msg = self.error_string()
        print(err_msg)
        # send updated image back to client
        try:
            with open(self._new_img,'rb') as f:
                for chunk in iter(lambda: f.read(CHUNK_SIZE), b''):
                    # print(chunk)
                    if not chunk:
                        break
                    img_return = image_pb2.ImageReturn(
                        image_type = self._img_type,
                        img_chunk_data = chunk,
                        filename = self._new_img,
                        errors = err_msg)
                    yield img_return
        except Exception as e:
            print(e)
        
        # delete the stored file
        os.remove(self._new_img)
        
        # send back an empty return to indicate next file being sent
        img_return = image_pb2.ImageReturn(
                        image_type = "",
                        img_chunk_data = b"",
                        filename = NEW_FILE_INCOMING,
                        errors = err_msg)
        yield img_return

        # send back thumbnail, if any
        if self._new_thumbnail is not None:
            try:
                with open(self._new_thumbnail,'rb') as f:
                    for chunk in iter(lambda: f.read(CHUNK_SIZE), b''):
                        # print(chunk)
                        if not chunk:
                            break
                        img_return = image_pb2.ImageReturn(
                            image_type = self._img_type,
                            img_chunk_data = chunk,
                            filename = self._new_thumbnail,
                            errors = err_msg)
                        yield img_return
            except Exception as e:
                print(e)
            # delete the stored file
            os.remove(self._new_thumbnail)
    
    def error_string(self):
        error_msg = ""
        for err in self._errs:
            error_msg += f"{err[0]}, {err[1]}\n"
        return error_msg