"""
ImageProcessor class handles image transformations using the OpenCV image 
library. Supports flip, rotate, greyscale, resizing, and thumbnail images in
version 1.0.

Author: Connor Hodges
Date: Februrary-March 2024
Institution: Seattle University
Version: 1.0
"""

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
GREYSCALE = "greyscale"
RESIZE = "resize"
THUMBNAIL = "thumbnail"
HORIZONTAL = "horizontal"
VERTICAL = "vertical"

# Constants used in comparisons and commands
RIGHT_DEGREES = -90
LEFT_DEGREES = 90
THUMBNAIL_SIZE = 200 
MAXIMUM_PERCENT = 500
MINIMUM_PERCENT = -95
MINIMUM_ROTATION = -10000
MAXIMUM_ROTATION = 10000
HORIZ_FLIP = 1
VERT_FLIP = 0
DEGREES_MODULO = 360

# codes
SUCCESS_200 = 200
ERROR_400 = 400


def uuid_generator(filetype):
    """
    Returns a uuid4 along with the image type
    """
    return str(str(f"{uuid.uuid4()}.{filetype}"))

class IImageProcessor(abc.ABC):
    """
    Abstract class for ImageProcessing. Must inherit from the processImage class
    to corrrectly inherit from the IImageProcessor.
    """
    @abc.abstractmethod
    def process_image(self):
        pass

class ImageProcessor(IImageProcessor):
    """
    ImageProcessor class inherits from IImageProcessor. Class object is created
    and iterates through a list of commands. Returns a modified image as well
    as errors, and thumbnails (if requested).
    """
    def __init__(self, img, string_cmds, img_type):
        """
        Class constructor to set values and convert commands too a list
        """
        self._img = img
        self._cmds = self._cmds_to_list(string_cmds)
        self._img_type = img_type
        self._new_img = None
        self._new_thumbnail = []
        self._errs = None 
    
    def _cmds_to_list(self, string_cmds):
        """
        Converts a string into a list based on new lines
        """
        rows = string_cmds.split("\n")
        new_list = []
        for row in rows:
            updated = row.split()
            new_list.append(updated)
        return new_list

    
    def process_image(self):
        """
        Processes the image. Iterates through the list of commands and returns
        the image, thumbnails, and errors to the caller
        """
        # iterate over all commands
        errs = []
        img = cv2.imread(self._img)
        updated_imgs = dict(img=img,
                            img_name=None,
                            thumbnail=[],
                            thumbnail_name=[])
        for cmd in self._cmds:
            updated_imgs, errs = self._execute_cmd(updated_imgs, cmd, errs)
        
        # add a 200 response if no errors
        if len(errs) == 0:
            errs.append((SUCCESS_200, "Sucessfully processed image"))
        self._errs = errs

        # write img to file to use to stream back to client    
        updated_imgs['img_name'] = uuid_generator(self._img_type)
        cv2.imwrite(updated_imgs['img_name'], updated_imgs['img'])
        self._new_img = updated_imgs['img_name']

        # Write thumbnails to file to prepare for transmission 
        if len(updated_imgs['thumbnail']) != 0:
            for i in range(len(updated_imgs['thumbnail'])):
                updated_imgs['thumbnail_name'].append(uuid_generator(self._img_type))
                cv2.imwrite(updated_imgs['thumbnail_name'][i], updated_imgs['thumbnail'][i])
                self._new_thumbnail.append(updated_imgs['thumbnail_name'][i])
        
        # return image, thumbnails, errors, and type of image for use in server
        return self._new_img, self._new_thumbnail, self._errs, self._img_type


    def _execute_cmd(self, imgs, cmd, errs):
        """
        Processes the first chunk of a command and interprets the command to an
        associated function. The command is called and the return value is 
        returned from the call back to _execute_cmd()'s caller.
        """
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
        try:
            # get commands from the paramter
            flip_type = cmd[1]
            if flip_type == HORIZONTAL:
                flip_cmd = HORIZ_FLIP
            elif flip_type == VERTICAL:
                flip_cmd = VERT_FLIP
            else:
                raise TypeError(f"['{flip_type}'] invalid parameter. Usage: flip <horizontal/vertical>")
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
        try:
            # set degrees to the cmd argument, then test if string command followed 
            # by casting as an int
            degrees = cmd[1]
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
                    self._check_rotation_amt(degrees)
                    rotation = degrees % DEGREES_MODULO if degrees >= 0 else (-1 * ((-1 * degrees) % DEGREES_MODULO))
                    rotation *= -1
                except ValueError as ve:
                    errs.append((ERROR_400, f"'{cmd[1]}' is invalid rotation parameters. Only integers allowed"))
                    return imgs, errs
                except Exception as e:
                    errs.append((ERROR_400, e))
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
            percent_change = int(cmd[1])
            self._check_dimension(percent_change)
            factor = self._convert_to_factor(percent_change)
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
        """
        Converts the provided image to a thumbnail of size 200 x 200 pixels. The
        thumbnail is appended to a list of thumbnails and does not replace any
        image.
        """
         # get commands from the paramter
        try:
            # self._check_thumbnail_prescence(imgs)
            new_size = (int(cmd[1]), int(cmd[2]))
            # imgs['thumbnail'] = cv2.resize(imgs['img'], new_size)
            imgs['thumbnail'].append(cv2.resize(imgs['img'], new_size))
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
        """
        checks the scaling factor and raises a ValueError if greater than 500%
        or less than -95%
        """
        if percent > MAXIMUM_PERCENT:
            raise ValueError("Cannot resize/scale by more than 500%")
        elif percent < MINIMUM_PERCENT:
            raise ValueError("Cannot resize/scale by less than -95%")
    

    def _check_rotation_amt(self, rotation):
        """
        checks the rotation amount of a rotation call and returns an exception 
        if less than -10000 degrees or greater than 10000 degrees
        """
        if rotation < MINIMUM_ROTATION:
            raise Exception("Rotation must be greater than -10001 degrees")
        if rotation > MAXIMUM_ROTATION:
            raise Exception("Rotation must be less than 10001 degrees")
    

    def _convert_to_factor(self, percent):
        """
        Converts a user provided percent scaling to a scaling factor value.
        """
        if percent >= 0:
            return (percent / 100) + 1
        if percent < 0:
            return 1 - (abs(percent) / 100)