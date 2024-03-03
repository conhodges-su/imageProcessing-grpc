# ref: https://www.youtube.com/watch?v=WB37L7PjI5k&t=206s >>> grpc basics and client/server setup
"""
IDEAS:
- the stream needs to collect on requests into the image plus,
"""

from concurrent import futures
import time
import uuid
import grpc
import image_pb2
import image_pb2_grpc
import image_processor as ip
import os

CHUNK_SIZE = 64 * 1024 # 64 KiB
NEW_FILE_INCOMING = "NEW_FILE_INCOMING"


def uuid_generator(filetype):
    return str(str(f"{uuid.uuid4()}.{filetype}"))


class ImageProcessorServicer(image_pb2_grpc.ImageProcessorServicer):
    def ProcessImage(self, request_iterator, context):
        img_return = image_pb2.ImageReturn()
        img_binary = b''
        ops = ""
        img_type = ""
        i = 0
        for request in request_iterator:
            ops = request.image_ops
            img_type = request.image_type
            img_binary += request.chunk_data
            i += 1
        
        # write the file to binary so processor class can read
        temp_filename = str(f"{uuid.uuid4()}.{img_type}")
        with open(temp_filename, 'wb') as outfile:
            outfile.write(img_binary)
        
        # pass the image to the processor class
        img_proc = ip.ImageProcessor(temp_filename, ops, img_type)

        # process image and collect errors and names to transmit back
        img, thumbs, errs, type = img_proc.process_image()
        # delete temporary file
        os.remove(temp_filename)

        # return the images back to the client
        yield from self.transmit_img(img, thumbs, errs, type)
    

    def transmit_img(self, img, thumbnails, errs, type):
        """
        ref: https://stackoverflow.com/questions/4566498/what-is-the-idiomatic-way-to-iterate-over-a-binary-file
        """
        
        # prepare error string
        err_msg = self.error_string(errs)
        # send updated image back to client
        try:
            with open(img,'rb') as f:
                for chunk in iter(lambda: f.read(CHUNK_SIZE), b''):
                    # print(chunk)
                    if not chunk:
                        break
                    img_return = image_pb2.ImageReturn(
                        image_type = type,
                        img_chunk_data = chunk,
                        filename = img,
                        file_num = 0,
                        errors = err_msg)
                    yield img_return
        except Exception as e:
            print(e)
        
        # delete the stored file
        os.remove(img)
        
        # send back an empty return to indicate next file being sent
        img_return = image_pb2.ImageReturn(
                        image_type = "",
                        img_chunk_data = b"",
                        filename = NEW_FILE_INCOMING,
                        file_num = 0,
                        errors = err_msg)
        yield img_return

        # send back thumbnail(s), if any
        if len(thumbnails) != 0:
            for i in range(len(thumbnails)):
                # Iterate over list of thumbnail images
                try:
                    with open(thumbnails[i],'rb') as f:
                        for chunk in iter(lambda: f.read(CHUNK_SIZE), b''):
                            if not chunk:
                                break
                            img_return = image_pb2.ImageReturn(
                                image_type = type,
                                img_chunk_data = chunk,
                                filename = thumbnails[i],
                                file_num = i,
                                errors = err_msg)
                            yield img_return
                except Exception as e:
                    print("error happening during open")
                
                # if additional images to transmit, add indicator to stream
                if i < len(thumbnails) - 1:
                    img_return = image_pb2.ImageReturn(
                                    image_type = "",
                                    img_chunk_data = b"",
                                    filename = NEW_FILE_INCOMING,
                                    file_num = i + 1,
                                    errors = err_msg)
                    yield img_return
                    
                # delete the stored file
                os.remove(thumbnails[i])

    
    def error_string(self, errs):
        error_msg = ""
        for err in errs:
            error_msg += f"{err[0]}, {err[1]}\n"
        return error_msg


def serve():
    # setup server with up to 100 workers
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=100))
    # add ImageProcessorServer to the server to receive requests
    image_pb2_grpc.add_ImageProcessorServicer_to_server(
        ImageProcessorServicer(),
        server)

    # keep localhost for now
    server.add_insecure_port("localhost:10760")
    server.start()
    print("started")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()