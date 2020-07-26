## blackhole

The name of the tool comes from the need that led me to write it. Basically
`blackhole` is the name of a challenge in the `Misc` section of the famous
Web CTF platform [hackthebox.eu](hackthebox.eu). One whose  flag resonated
very well with my feelings of that time.

#### Purpose

The purpose of the tool is to allow execution of many instances of a given
command/executable simultaneously. The command then should take as argument,
among others, a string taken from a row of a given text file. To be able to
distinguish a successful case (the one that lead to stopping all instances)
from the failing ones the tool let the user give a model, in form of regular
expression, that univocally identify the string emitted by the executable on
the standard output when its purpose is fulfilled.

To better grasp what said above let's shed some light through an example.
Using the tool a user can start many instances of a cli application for
deciphering files: each instance will receive as one of its argument a key
taken from a password list, realizing  in facts a brute force attack based
on given wordlist.

#### Install

The easiest and cleanest way to use the tool is to clone the GitHub 
repository and execute the downloaded source code directly from there.
Here is one possibile way to achieve that:

````shell script

# Cloning the repository
git clone https://github.com/GiovaLomba/blackhole

# Moving into the cloned repository
cd blackhole
````

Once done, you are ready to install requirements and run the tool
the way you need.

#### Requirements

1. Python 3.8.x - Because of usage in the source of the walrus operator.
2. colorama - A package to simplify the emission of ANSI color codes. 

In order to install requirements and keep them separated from other tools
run the following commands:

````shell script

# Creates an isolated virtual environment for the project
virtualenv -p $(which python3.8) blackhole_env

# Activate the newly created environment
source blackhole_env/bin/activate

# Install requirements
pip install < requirements.txt

````

#### Help

What follows is the full help string of the tool as displayed when it's 
invoked from the command line with the double dash help option `--help`:

```shell script
blackhole.py --help
(c) 2020 Giovanni Lombardo mailto://g.lombardo@protonmail.com
blackhole.py version 1.0.0

usage: blackhole.py [-h] [-p P] wordlist command [command ...] pattern

It runs a command against a given word list file until a certain pattern in
the output is met or not.

positional arguments:
  wordlist              The wordlist file.
  command               The command and its arguments [%% indicates password
                        position].
  pattern               The pattern in the output indicating the command
                        succeeded.

optional arguments:
  -h, --help            show this help message and exit
  -p P, --processors P  The number of processes to spawn simultaneously.
```

#### How I used the tool (a.k.a. example)

This is how I used the tool:

```shell script
user@host$ python blackhole.py \ 
              passwords.txt \                         # The wordlist 
              steghide extract @@p %% @@sf hawking \  # The command 
              (?i)found                               # The model
```

**IMPORTANT:**

As you can see in the example above, the command to perform contains
some `@` characters. This is done to avoid the command line argument
parser of the tool having to select manually what are its own arguments
and which are the ones for the command the user want to run. Then the
user is required to use a  `@` symbols in place of each dash `-` needed
by the command. `@` symbols will then be replaced at runtime by the tool
with dashes.
