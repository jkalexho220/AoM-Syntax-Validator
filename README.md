# AoM-Syntax-Validator
A python command-line tool that formats raw .xs code into code that Age of Mythology can read. Supports RMS as well as trigger .xml output

## Uses
There are two python files: **rmsify.py** and **xmlify.py**. **rmsify.py** is used to generate Random Map Scripts. **xmlify.py** is used to generate trigger code that can be used in custom scenarios.

These files will read raw .xs code and perform syntax validation on it. Then it will produce an output file that AoM understands, depending on what you are trying to make.

It is important to note that the syntax validator only finds one error at a time. After it finds one error, you must fix that error before the validator can continue checking the rest of your code.

Sometimes, an error in your code will cause multiple error messages. Some of them are merely side effects of the true syntax error. (For example, if you gave bad input to a function, not only will it trigger a "bad input" error, it may also trigger an "unrecognized token" error). When this happens, usually the very first or last error reported is the true cause of the syntax error. Fix it and you should be good to go.

## Xmlify (AoM trigger code generator)
To setup xmlify.py, create a new folder and move xmlify.py, Commands.xml, and the template.txt files to it. Next, open xmlify.py and modify the FILES, FILENAME, and NAME fields.
* FILENAME: The name of the .xml output file
* NAME: The name of the trigger effect that will be created
* FILES: The list of files, _in order_ that will be parsed. These are plaintext files, though saving them as .c can help your IDE understand and highlight syntax more accurately.

To run xmlify.py, navigate to your folder with a command line tool and run the following command:
> python xmlify.py

This will produce a .xml file containing a single trigger effect that has all your code from the various files you listed in the Files field. You can then then copy this file to your trigger2 folder. Add it to your scenario as an effect in an inactive trigger and it will run the entirety of your code.

## Rmsify (Random Map Script code generator)
To setup rmsify.py, create a new folder for your project. Move the rmsify.py and the Commands.xml files to this folder. Then create a folder named XS under your folder. Next, open up rmsify.py and modify the FILENAME and FILES fields.
* FILENAME: The name of the .xs output file
* FILES: The list of files, _in order_ that will be parsed. These are plaintext files, though saving them as .c can help your IDE understand and highlight syntax more accurately.
* rmsFunc: The file that contains declarations for custom RMS function.
* rmsMain: The file that contains RMS code that exists in void main() of the RMS.

Files in the FILES list should contain trigger code only. However, there is a way to inject RMS code into your trigger code. To do so, use a % symbol on a new line to exit trigger code and enter RMS code. When you are done with RMS code injection, use another % symbol on its own line to re-enter trigger code.

Once you are done editing your code, you can run rmsify.py by navigating to your folder with a command line tool and running the following command:
> python rmsify.py

This will produce a .xs file in your XS folder, which you can then copy to your rm2 folder and run as a random map script. (Note that a random map script requires two files: a .xml and .xs file. Their names must also match. This program only produces the .xs file. You can open another random map script's .xml file to see how it is written)

There are also several command-line options that you can add:
**-t** (Tabs) The output file will also contain your tab indentation and whitespace
**-r** (Reformat) Your code will be automatically modified to have proper indentation
**-c** (Comments) Multi-line comments will be included in the output file (but not single-line comments)
**-v** (Verbose) Not very useful unless you're me trying to debug the python files. This will print out the code in real-time revealing how it's being parsed by the program.
