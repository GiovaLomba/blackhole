## blackhole

The name of the tool comes from the need that lead me to write it. 
Basically `blackhole` is the name of a challenge in the `Misc` 
section of the very famous CTF web platform [hackthebox.eu](hackthebox.eu) 
whose flag resonated very well with my feelings of the time. 

#### Purpose

The purpose of the tool is to execute many instances of a specified
command simultaneously taking the value of one of its argument from
a specified file. For example you can run many instances of an exe
file for decrypting giving it each time a different text as key 
taken from a file. To distinguish the successful case from the 
failed one the tool let you specify a regular expression identifying
a string emitted by the command on standard output when its purpose
is fulfilled.

#### Help

Here is the full help string of the tool as displayed when it's 
invoked with the double dash help option `--help`:

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
user@host$ blackhole.py passwords.txt steghide extract @@p %% @@sf hawking (?i)found
```

**IMPORTANT:**

As you can see in the example above, the command to perform contains 
some `@` characters. This is done to avoid the command line argument 
parser having to select manually what are its arguments and which the
ones for the command to perform. Then the user is required to use a 
`@` symbols for each dash `-` needed in the command. `@` symbols are
then replaced with dashes at runtime.
