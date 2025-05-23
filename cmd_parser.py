"""
The cmd_parser.py file handles the clietn side functionality to interact with
a gRPC-based server. The file requires that the image_pb2 and image_pb2_grpc
files are generated and and available to the caller.

Author: Connor Hodges
Date: Februrary-March 2024
Institution: Seattle University
Version: 1.0
"""

import abc
import grpc
import os
import image_pb2
import image_pb2_grpc

NEW_FILE_INCOMING = "NEW_FILE_INCOMING"
IMG_TYPES = ('jpg', 'jpeg', 'png', 'tif')

class ICmdParser(abc.ABC):
    """
    Abstract class for CmdParser. Must inherit implement the process_image()
    method to corrrectly inherit from the ICmdParser.
    """
    @abc.abstractmethod
    def process_image(self):
        pass

class CmdParser(ICmdParser):
    """
    The CmdParser class processes client side image requests by abstracting away
    communication with a gRPC-based server stub. Clients create instances of
    the CmdParser, passing the commands and image files for processing.
    """
    def __init__(self, src, cmds, host, port):
        """
        Constructor for the CmdParser class
        """
        self.src = src
        self.cmds = cmds
        self.host = host
        self.port = port
        self._img_type = self._get_image_type()

    
    def process_image(self):
        """
        Handles communication with an image server usign the host/port provided
        in the constructor. Image information is transmitted to the server and 
        results of the processing are collected by process_image and info
        returned to the client.
        """
        host_port = self.host + ":" + str(self.port)
        new_img = b""
        new_img_name = b""
        error_msg = b""
        encountered_thumbnail = False
        response_dict = dict(
            img="",
            thumbnail=[],
            responses=[]
        )
        new_thumbnail = []
        new_thumbnail_name = []
        file_num = 0

        # connect to gRPC server and establish channel stub`
        if self._is_supported_img():
            try:
                self._check_file_exists()
                with grpc.insecure_channel(host_port) as channel:
                    # connect to server, transmit, and receive images
                    stub = image_pb2_grpc.ImageProcessorStub(channel)
                    processed_img = stub.ProcessImage(self._transmit_img())
                    
                    # iterate through chunks to collect images and errors (if any)
                    for process in processed_img:
                        error_msg = process.errors
                        file_num = process.file_num

                        # check if encountered sentinel to indicate to skip
                        # this message frame for image
                        if process.filename == NEW_FILE_INCOMING and not encountered_thumbnail:
                            encountered_thumbnail = True
                            new_thumbnail.append(b"")
                            new_thumbnail_name.append(b"")
                            continue

                        # Skip message frame to process another thumbnail
                        if process.filename == NEW_FILE_INCOMING:
                            new_thumbnail.append(b"")
                            new_thumbnail_name.append(b"")
                            continue
                        
                        # load images from the first image sent until thumbnail
                        if not encountered_thumbnail:
                            new_img_name = process.filename
                            new_img += process.img_chunk_data
                        else: 
                            new_thumbnail_name[file_num] = process.filename
                            new_thumbnail[file_num] += process.img_chunk_data
            except ValueError as ve:
                response_dict['img'] = None
                response_dict['thumbnail'] = None
                response_dict['responses'] = ve
                return response_dict
            except Exception as e:
                print(e)
                response_dict['img'] = None
                response_dict['thumbnail'] = None
                response_dict['responses'] = "500, Unable to connect to server"
                return response_dict
            else:    
                # save the errors to the dict
                response_dict['responses'] = self.convert_to_list(error_msg)
                
                # save the images to file
                with open(f"client_{new_img_name}", 'wb') as outfile:
                    outfile.write(new_img)
                    response_dict['img'] = f"client_{new_img_name}"
                # save thumbnail    
                if len(new_thumbnail_name) != 0:
                    for i in range(len(new_thumbnail_name)):
                        with open(f"client_{new_thumbnail_name[i]}", 'wb') as outfile:
                            outfile.write(new_thumbnail[i])
                            response_dict['thumbnail'].append(f"client_{new_thumbnail_name[i]}")
                # set it none if not included
                else:
                    response_dict['thumbnail'] = []
                return response_dict          
        else:
            print(f"Error: Image file, {self.src}, is not a supported type or missing file extension")
            response_dict['responses'] = "400, invalid file type/missing extension"
            return response_dict
    

    def _check_file_exists(self):
        """
        Checks if the image exists, if not a value error is raised
        """
        if not os.path.isfile(self.src):
            raise ValueError("404, file does not exist")

    def _transmit_img(self):
        """
        Transmits the image to the gRPC-based server using the protobuf 
        definition.
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
        """
        Checks the file type of the image to process. if not part of the types
        supported, false is return. else true.
        """
        if self._img_type not in IMG_TYPES:
            return False
        return True
    

    def _get_image_type(self):
        """
        Extracts the image type from the file name
        """
        chunks = self.src.split('.')
        length = len(chunks)
        # return no image type if no split occurs
        if length < 2:
            return None
        return chunks[length - 1]
    

    def convert_to_list(self, str_err):
        """
        Converts a string of errors separated by newlines and returns a list.
        """
        if str_err == "":
            return []
        error_list = str_err.split("\n")
        err_num = len(error_list)
        # remove extra index due to split on newline adding additional line
        if error_list[err_num - 1] == "":
            error_list = error_list[:err_num - 1]
        return error_list
    