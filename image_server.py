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



def uuid_generator(filetype):
    return str(str(f"{uuid.uuid4()}.{filetype}"))

class ImageProcessorServicer(image_pb2_grpc.ImageProcessorServicer):
    def ProcessImage(self, request_iterator, context):
        print("received request")
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
        img_proc.process_image()
        # delete temporary file
        os.remove(temp_filename)
        # print(errs)

        # return the images back to the client
        yield from img_proc.transmit_img()

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