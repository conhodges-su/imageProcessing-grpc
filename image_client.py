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


def success_one():
    # Prepare a list of commands (as strings)
    cmd1 = "rotate 40"
    cmd2 = "thumbnail"
    cmd3 = "greyscale"
    cmd4 = "resize 10"
    cmd5 = "flip vertical"
    cmds = [cmd1, cmd2, cmd3, cmd4, cmd5]

    # Create an instance of the CmdParser class, passing in the path to the file
    # the commands, and the host/port combination of the ImageProcessing server
    new_cmd = cmd.CmdParser(FILEPATH, cmds, "localhost", 10760)

    # Call `process_image() and retrieve the results`
    response = new_cmd.process_image()
    
    # Print the contents of the response to the terminal
    print("SCENARIO 1")
    print_results(response)

    show_images(response)


def success_two():
    # Prepare a list of commands (as strings)
    cmd1 = "rotate 40"
    cmd2 = "thumbnail"
    cmd3 = "resize 100"
    cmd4 = "flip vertical"
    cmd5 = "thumbnail"
    cmd6 = "greyscale"
    cmd7 = "thumbnail"
    cmds = [cmd1, cmd2, cmd3, cmd4, cmd5, cmd6, cmd7]

    # Create an instance of the CmdParser class, passing in the path to the file
    # the commands, and the host/port combination of the ImageProcessing server
    new_cmd = cmd.CmdParser(FILEPATH, cmds, "localhost", 10760)

    # Call `process_image() and retrieve the results`
    response = new_cmd.process_image()
    
    # Print the contents of the response to the terminal
    print("SCENARIO 2")
    print_results(response)

    show_images(response)


def failure():
    # Prepare a list of commands (as strings)
    cmd1 = "rotate 40"
    cmd2 = "hover"
    cmd3 = "greyscale"
    cmd4 = "resize -99"
    cmd5 = "flip over"
    cmds = [cmd1, cmd2, cmd3, cmd4, cmd5]

    # Create an instance of the CmdParser class, passing in the path to the file
    # the commands, and the host/port combination of the ImageProcessing server
    new_cmd = cmd.CmdParser(FILEPATH, cmds, "localhost", 10760)

    # Call `process_image() and retrieve the results`
    response = new_cmd.process_image()
    
    # Print the contents of the response to the terminal
    print("SCENARIO 3")
    print_results(response)

    show_images(response)

def print_results(response):
    print("---------------------------------------------------------------------")
    print(f"img file: \n\t1.{response['img']}")

    print("Thumbnail(s): ")
    for i in range(len(response['thumbnail'])):
        print(f"\t{i+1}. {response['thumbnail'][i]}")
    
    print("Response(s):")
    for i in range(len(response['responses'])):
        print(f"\t{i+1}. {response['responses'][i]}")
    print("---------------------------------------------------------------------")
    print()



def show_images(response):
    """
    LIVE IMAGE DEMONSTRATION
    """
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
    i = 1
    for pic in response['thumbnail']:
        thumb = cv2.imread(pic)
        cv2.imshow(f'thumbnail{i}', thumb)
        cv2.waitKey(0)
        i += 1

    # and finally destroy/close all open windows
    cv2.destroyAllWindows()


FILEPATH = "Nerd_Preview.png"
if __name__ == "__main__":

    success_one()
    success_two()
    failure()
