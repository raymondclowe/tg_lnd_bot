import subprocess
import sys

def runcmd(cmd, verbose = False, *args, **kwargs):
    ## run a command and return the output
    # returns three values, the stdout, stderr, and the return code

    process = subprocess.Popen(
        cmd,
        stdout = subprocess.PIPE,
        stderr = subprocess.PIPE,
        text = True,
        shell = True
    )
    std_out, std_err = process.communicate()
    errorlevel = process.returncode
    if verbose:
        print(std_out.strip(), std_err)
        if errorlevel:
            print(f"errorlevel : {errorlevel}")
    return std_out, std_err, errorlevel

    

# use __main__ to run a test if this file is run directly
if __name__ == '__main__':
    # if there is a url on the arguement line
    if len(sys.argv) > 1:
        cmdstring = sys.argv[1]
    else:
        cmdstring = 'echo Hello World'

    print(f"executing {cmdstring}")        
    output, error, errorlevel = runcmd(cmdstring)
    if output:
        print(output)
    else:
        if error:
            print(error)
        else:
            print(f"no output or error:  errorlevel = {errorlevel}")
