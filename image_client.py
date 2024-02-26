
import cmd_parser as cmd

FILEPATH = "Nerd_Preview.png"
if __name__ == "__main__":
    # execute("screenshot.png")
    cmds = "rotate +40"
    new_cmd = cmd.CmdParser(FILEPATH, cmds, "localhost", 10760)
    response = new_cmd.process_image()
    print(f"errors: {response['errors']}")
    print(response['img'])
    print(response['thumbnail'])