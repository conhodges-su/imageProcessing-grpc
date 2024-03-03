"""
Simple client that uses the CmdParser class to connect to an imageProcessing
server. Displays the results to the screen.

Author: Connor Hodges
Date: Februrary-March 2024
Institution: Seattle University
Version: 1.0
"""

import cv2
import cmd_parser as cmd

FILEPATH = "Nerd_Preview.png"
if __name__ == "__main__":
    cmd1 = "rotate 20"
    cmd2 = "thumbnail"
    cmd3 = "greyscale"
    cmd4 = "resize 10"
    cmds = [cmd1, cmd2, cmd3, cmd4]
    new_cmd = cmd.CmdParser(FILEPATH, cmds, "localhost", 10760)
    response = new_cmd.process_image()
    
    print(f"img file: {response['img']}")
    print(f"thumbnail file: {response['thumbnail']}")
    print(f"errors: {response['errors']}")

    # print the image to screen
    # read image 
    image = cv2.imread(FILEPATH)
    # show the image, provide window name first
    cv2.imshow('image window', image)
    # add wait key. window waits until user presses a key
    cv2.waitKey(0)

    new_img = cv2.imread(response['img'])
    cv2.imshow('image window', new_img)
    # add wait key. window waits until user presses a key
    cv2.waitKey(0)

    # show the thumbnails
    for pic in response['thumbnail']:
        thumb = cv2.imread(pic)
        cv2.imshow('thumbnail', thumb)
        cv2.waitKey(0)

    # and finally destroy/close all open windows
    cv2.destroyAllWindows()