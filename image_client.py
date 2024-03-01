
import cmd_parser as cmd

FILEPATH = "Nerd_Preview.png"
if __name__ == "__main__":
    # execute("screenshot.png")
    cmd1 = "rotate +40"
    cmd2 = "thumbnail"
    cmd3 = "greyscale"
    cmd4 = "thumbnail"
    cmds = [cmd1, cmd2, cmd3, cmd4]
    new_cmd = cmd.CmdParser(FILEPATH, cmds, "localhost", 10760)
    response = new_cmd.process_image()
    print(response['errors'])
    print(response['img'])
    print(response['thumbnail'])