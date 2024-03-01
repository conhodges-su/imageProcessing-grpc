import grpc
import image_pb2
import image_pb2_grpc

NEW_FILE_INCOMING = "NEW_FILE_INCOMING"
IMG_TYPES = ('jpg', 'jpeg', 'png', 'gif', 'tif')

class ICmdParser():
    def __init__(self, src, cmds, host, port):
        pass

    def process_image(self):
        pass

class CmdParser():
    def __init__(self, src, cmds, host, port):
        self.src = src
        self.cmds = cmds
        self.host = host
        self.port = port
        self._img_type = self._get_image_type()

    
    def process_image(self):
        host_port = self.host + ":" + str(self.port)
        new_img = b""
        new_img_name = b""
        new_thumbnail = b""
        new_thumbnail_name = b""
        error_msg = b""
        encountered_thumbnail = False
        response_dict = {}

        # connect to gRPC server and establish channel stub`
        if self._is_supported_img():
            try:
                with grpc.insecure_channel(host_port) as channel:
                    # connect to server, transmit, and receive images
                    stub = image_pb2_grpc.ImageProcessorStub(channel)
                    processed_img = stub.ProcessImage(self._transmit_img())
                    
                    # iterate through chunks to collect images and errors (if any)
                    for process in processed_img:
                        error_msg = process.errors
                        # check if encountered sentinel to indicate to skip
                        # this message frame
                        if process.filename == NEW_FILE_INCOMING:
                            encountered_thumbnail = True
                            continue
                        
                        # load images from the first image sent until thumbnail
                        if not encountered_thumbnail:
                            new_img_name = process.filename
                            new_img += process.img_chunk_data
                        else: 
                            new_thumbnail_name = process.filename
                            new_thumbnail += process.img_chunk_data

            except Exception as e:
                response_dict['errors'] = "500, Unable to connect to server"
                return response_dict
            else:    
                # save the errors to the dict
                response_dict['errors'] = error_msg
                
                # save the images to file
                with open(f"client_{new_img_name}", 'wb') as outfile:
                    outfile.write(new_img)
                    response_dict['img'] = f"client_{new_img_name}"
                # save thumbnail    
                if new_thumbnail_name:
                    with open(f"client_{new_thumbnail_name}", 'wb') as outfile:
                        outfile.write(new_thumbnail)
                        response_dict['thumbnail'] = f"client_{new_thumbnail_name}"
                # set it none if not included
                else:
                    response_dict['thumbnail'] = None
                return response_dict          
        else:
            print(f"Error: Image file, {self.src}, is not a supported type or missing file extension")
            response_dict['errors'] = "400, invalid file type/missing extension"
            return response_dict
    

    def _transmit_img(self):
        """
        ref: https://stackoverflow.com/questions/4566498/what-is-the-idiomatic-way-to-iterate-over-a-binary-file
        """
        str_cmds = "\n".join(self.cmds)
        CHUNK_SIZE = 64 * 1024 # 64 KiB
        # send image to server in chunks
        try:
            with open(self.src,'rb') as f:
                for chunk in iter(lambda: f.read(CHUNK_SIZE), b''):
                    if not chunk:
                        break
                    img_request = image_pb2.ImageRequest(
                        image_ops = str_cmds,
                        image_type = self._img_type,
                        chunk_data = chunk)
                    yield img_request
        except Exception as e:
            print(e)
    
    def _is_supported_img(self):
        if self._img_type not in IMG_TYPES:
            return False
        return True
    

    def _get_image_type(self):
        chunks = self.src.split('.')
        length = len(chunks)
        # return no image type if no split occurs
        if length < 2:
            return None
        return chunks[length - 1]
    