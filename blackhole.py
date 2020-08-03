"""
It runs a command against a given word list file until
a given pattern is emitted and found on standard output.
"""

from argparse import ArgumentParser, Namespace
from colorama import Fore, Style, AnsiToWin32, init as colorama_init
from logging import NOTSET, INFO, WARNING, ERROR, DEBUG
from logging import getLogRecordFactory, setLogRecordFactory, basicConfig, getLogger, LogRecord
from multiprocessing import Pool, RLock, cpu_count
from os import environ, listdir, access, R_OK, X_OK, getpid, kill
from os.path import basename, pathsep, join as path_joiner
from pathlib import Path
from platform import system as system_platform
from re import findall, DOTALL, MULTILINE, compile as re_compile
from signal import signal, SIGINT, SIG_IGN
from subprocess import run, PIPE, STDOUT
from sys import argv, stdout
from timeit import timeit
from types import FrameType
from typing import Any, Dict, List, Optional as Opt


major = 1
minor = 0
fixes = 0

pool_objects = dict()
screen_lock = RLock()


class LoggingRecordFactoryColorama:
    """
    It adds the 'color' and 'reset' attributes to the LogRecord instance produced by the existing LogRecord.
    """

    levels_map = {
        INFO: Fore.LIGHTBLUE_EX + Style.DIM,
        DEBUG: Fore.GREEN + Style.BRIGHT,
        WARNING: Fore.LIGHTYELLOW_EX + Style.DIM,
        ERROR: Fore.LIGHTRED_EX + Style.DIM,
        NOTSET: Fore.RESET
    }

    color_attr = 'color'
    reset_attr = 'reset'

    def __init__(self, level_map: Opt[Dict[int, str]] = None, existing_factory: Any = getLogRecordFactory()) -> None:
        """
        It creates an instance of the LoggingRecordFactoryColorama class with the given level_map and existing_factory.

        :param level_map:           The dictionary mapping levels to colors.
        :type level_map:            Opt[Dict[int, str]].
        
        :param existing_factory:    The default LogRecordFactory to be used.
        :type existing_factory:     Any.
        """
        self.levels_map = level_map if level_map else self.__class__.levels_map
        self.existing_factory = existing_factory
        setLogRecordFactory(self)

    def __call__(self, *args: Any, **kwargs: Any) -> LogRecord:
        """
        It adds the color_attr and reset_attr attribute's values  according to the given levels_map, to the kwargs of
        the record built and returned by the existing_factory, and returns it to the caller.

        :param args:    The positional args to pass to the existing_factory.
        :type args:     Any.
        
        :param kwargs:  The keyword arguments to pass to the existing_factory.
        :type kwargs:   Any.

        :return: The record with the new arguments added.
        :rtype: LogRecord.
        """
        record = self.existing_factory(*args, **kwargs)
        setattr(record, self.__class__.color_attr, self.levels_map[record.levelno])
        setattr(record, self.__class__.reset_attr, self.levels_map[NOTSET])
        return record


def logging_console_init(level: int = INFO) -> None:
    """
    It initializes the default logging configuration.
    
    :param level:   The wanted logging level.
    :type level:    int.

    :return: None.
    :rtype: None.
    """

    color_attr = LoggingRecordFactoryColorama.color_attr
    reset_attr = LoggingRecordFactoryColorama.reset_attr
    stream = stdout if 'Windows' not in system_platform() else AnsiToWin32(stdout).stream
    colorama_init()

    # Removed from the format key of config for efficiency in space and time:
    #   [%(asctime)s.%(msecs)03d]         --> date and time in the given datefmt
    #   [%(processName)s.%(process)d]     --> process name dot process id
    #   [%(levelname)s]                   --> level name

    # Removed from the datefmt key of config for efficiency in space and time:
    #   %Y/%m/%d %H:%M:%S'                --> the format of the date in asctime when given

    config = dict(
        level=level,
        stream=stream,
        format=f'%({color_attr})s%(message)s%({reset_attr})s',
    )

    basicConfig(**config)
    LoggingRecordFactoryColorama()


def author() -> str:
    """
    It returns a brief string giving credits to the authors.

    :return: See description.
    :rtype: str.
    """
    return '(c) 2020 Giovanni Lombardo mailto://g.lombardo@protonmail.com'


def version() -> str:
    """
    It returns a version string for the current program.

    :return: See description.
    :rtype: str.
    """
    global major, minor, fixes
    return '{0} version {1}\n'.format(basename(argv[0]), '.'.join(map(str, [major, minor, fixes])))


def init_workers(command: List[str], pattern: str) -> None:
    """
    This routing serves as initialization procedure for processes owned
    by a process pool. It creates on the global variable pool_objects a
    key whose corresponding value is the PID of the current process that
    will execute the given command looking in its output for the given
    pattern.

    :param command:     The command along with its arguments.
    :type command:      List[str].

    :param pattern:     The pattern to look for.
    :type pattern:      str.

    :return: None.
    :rtype: None.
    """

    global pool_objects
    signal(SIGINT, SIG_IGN)
    logging_console_init()
    pool_objects[getpid()] = dict(
        command=command,
        pattern=re_compile(pattern, DOTALL | MULTILINE)
    )


def sigint_handler(signum: int, frame: FrameType) -> None:
    """
    The handler registered for SIGINT signal handling.
    It terminates the application.

    :param signum:  The signal to be handled.
    :type signum:   int.

    :param frame:   The current frame.
    :type frame:    FrameType.

    :return: See description.
    """
    global screen_lock
    logger = getLogger(__name__)

    with screen_lock:
        logger.info(f'Interrupt received: {signum}.')
        logger.info(f'{frame}')
        exit(0)


def can_perform(performer):
    """
    It tells whether the given performer can be executed on the current environment.

    :param performer:	The performer.
    :type performer: 	str.

    :return: Whether or not the given performer can be run on the current environment.
    :rtype: bool.
    """
    logger = getLogger(__name__)
    for path in environ['PATH'].split(pathsep):
        if not access(path, R_OK):
            logger.warning('Access to \'%s\' denied.' % path)
            continue
        if performer in listdir(path) and access(path_joiner(path, performer), X_OK):
            return True
    return False


def perform(row: str, master_pid: int) -> None:
    """
    It performs the command using the given row as value for the placeholder.

    :param row:         The row to inject as parameter for the command.
    :type row:          str.

    :param master_pid:  The pid of the master process.
    :type master_pid:   int.

    :return: None.
    :rtype: None.
    """
    global pool_objects
    obj = pool_objects[getpid()]
    logger = getLogger(__name__)
    cmd = ' '.join(obj['command']).replace('%%', f'{row}').split()
    ret = run(cmd, stdout=PIPE, stderr=STDOUT)

    if len(findall(obj['pattern'], str(ret.stdout))) > 0 and ret.check_returncode():
        with screen_lock:
            logger.info('\n** FOUND **: \'{0}\''.format(row))
            stdout.flush()
            kill(master_pid, SIGINT)


def usage(args: List[str]) -> Namespace:
    """
    It parses the given args (usually from sys.argv) and checks they
    conform to the rules defined by the argument parser. Then it returns
    a namedtuple having a field for a any given or defaulted argument.

    :param args:    The command line arguments to be parsed.
    :type args:     List[str].

    :return: See description.
    :rtype: NamedTuple.
    """
    helps = dict(
        description=__doc__,
        wordlist='The wordlist file.',
        command='The command with its arguments [%% indicates password position].',
        pattern='The pattern in the output indicating the command succeeded.',
        processors='The number of processes to spawn simultaneously.',
        encoding='The encoding the wordlist is encoded with.'
    )

    logger = getLogger(__name__)
    parser = ArgumentParser(description=helps['description'])
    parser.add_argument('wordlist', help=helps['wordlist'])
    parser.add_argument('command', nargs='+', help=helps['command'])
    parser.add_argument('pattern', help=helps['pattern'])
    parser.add_argument('-p', '--processors', type=int, dest='p', default=cpu_count(), help=helps['processors'])
    parser.add_argument('-e', '--encoding', type=str, dest='e', default='utf-8', help=helps['encoding'])

    args = parser.parse_args(args)

    args.p = abs(args.p)
    args.wordlist = Path(args.wordlist)

    if not args.wordlist.exists():
        logger.error(f'The `wordlist` file must exists: {str(args.wordlist)}.')
        parser.print_usage()
        exit(1)

    if not args.wordlist.is_file():
        logger.error(f'The `wordlist` argument must be a file: {str(args.wordlist)}.')
        parser.print_usage()
        exit(1)

    if not access(args.wordlist, R_OK):
        logger.error(f'The `wordlist` argument must be readable: {str(args.wordlist)}.')
        parser.print_usage()
        exit(1)

    if len(args.command) < 2 or '%%' not in args.command:
        logger.error(f'The `command` value must contain at least command and placeholder: {str(args.command)}.')
        parser.print_usage()
        exit(1)

    if not can_perform(args.command[0]):
        logger.error(f'The `command` {str(args.command)} cannot be found in PATH.')
        parser.print_usage()
        exit(1)

    for idx in range(1, len(args.command)):
        if args.command[idx].startswith('@@'):
            args.command[idx] = args.command[idx].replace('@@', '-')

    return args


def main(args: Namespace) -> None:
    """
    It starts the application.

    :param args:    The parsed command line arguments as returned by usage();
    :type args:     Namespace.

    :return: None.
    :rtype: None.
    """
    logger = getLogger(__name__)

    try:

        pool = Pool(
            args.p,
            initializer=init_workers,
            initargs=(args.command, args.pattern)
        )

        master_pid = getpid()
        with open(str(args.wordlist), 'r', errors='ignore', encoding=args.e) as f:
            for index, line in enumerate(f):
                logger.info(f'{index:_>10}:{line[:-1]}')
                r = pool.apply_async(
                    func=perform,
                    args=(line[:-1], master_pid),
                    error_callback=lambda x: (print(str(x)) and kill(master_pid, SIGINT) and exit(1))
                )

                if index != 0 and 0 == index % 36:
                    r.get()

        pool.close()
        pool.join()

    except (IOError, OSError, Exception) as e:
        logger.error(f'{str(e)}')
        exit(1)


def external_main(args: List[str]) -> None:
    """
    The procedure that allows realization of standalone applications.

    :param args:    The command line arguments to be parsed by the application.
    :type args:     List[str].

    :return: None.
    :rtype: None.
    """
    logging_console_init()
    logger = getLogger(__name__)
    signal(SIGINT, sigint_handler)
    print(author())
    print(version())

    logger.info(f'\nElapsed time: {timeit(stmt=lambda: main(usage(args)), number=1):.4f} sec.')


if __name__ == '__main__':
    external_main(argv[1:])
