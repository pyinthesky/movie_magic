"""
This is a quick and dirty way to get a nice list of rankings for movies using the
Open Movie Database API. You can provide either a list of movies, or point the script at
a folder. It will do a half-way-decent job of trying to clean up the file names for submission.
On a failed submit, the movie will have a score of 0.

To use the script, you will need to get an api key via a very quick and immediate email
response.

The final score is the aggregate from whatever rating sources OMD had
"""


import urllib.request
import argparse
import os
import pprint
import re
import json
import errno
import glob
import traceback


RESULTS_FN  = "movie_magic_results.txt"
RESULTS_RAW = "movie_magic_results_raw.txt"
API_KEY     = ""
OMD_URL     = "http://www.omdbapi.com/?i=tt3896198&apikey=%s&t=" % API_KEY
EXTENSIONS  =   [
                    '264',
                    '3g2',
                    '3gp',
                    'arf',
                    'asf',
                    'asx',
                    'avi',
                    'bik',
                    'dash',
                    'dat',
                    'dvr',
                    'flv',
                    'h264',
                    'm2t',
                    'm2ts',
                    'm4p',
                    'm4v',
                    'mkv',
                    'mod',
                    'mov',
                    'mp2',
                    'mp4',
                    'mpe',
                    'mpeg',
                    'mpg',
                    'mpv',
                    'mts',
                    'ogg',
                    'ogv',
                    'prproj',
                    'qt',
                    'rec',
                    'rmvb',
                    'swf',
                    'tod',
                    'tp',
                    'ts',
                    'vob',
                    'webm',
                    'wlmp',
                    'wmv'
                 ]
ALTERNATE_TITLES    =   {
                            "&":"and",
                            "1":"i",
                            "2":"ii",
                            "3":"iii",
                            "4":"iv",
                            "5":"v",
                            "6":"vi",
                            "7":"vii",
                            "8":"viii",
                            "9":"ix",
                            "10":"x",
                            # "i":"1",
                            # "ii":"2",
                            # "iii":"3",
                            # "iv":"4",
                            # "v":"5",
                            # "vi":"6",
                            # "vii":"7",
                            # "viii":"8",
                            # "ix":"9",
                            # "x":"10",
                        }

class DirectoryValidation(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        for val in values:
            if os.path.exists(val) and os.path.isdir(val):
                MovieMagic.DIRECTORY_LIST.append(val)
            else:
                raise ValueError("%s is not a valid directory", val)


class OutputValidation(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if os.path.exists(values) and os.path.isdir(values):
            MovieMagic.OUTPUT_FILE_DIR = values
        else:
            raise ValueError("%s is not a valid directory", values)


class FileValidation(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        for val in values:
            if os.path.exists(val) and not os.path.isdir(val):
                try:
                    with open(val) as f:
                        _ = f.read()
                except IOError as x:
                    if x.errno == errno.ENOENT:
                        raise IOError("%s - does not exist", val)
                    elif x.errno == errno.EACCES:
                        raise IOError("%s - cannot be read", val)
                    else:
                        raise IOError("%s - some other error", val)
                else:
                    MovieMagic.DIRECTORY_LIST.append(val)
            else:
                raise ValueError("%s is not a valid directory", val)

class SetVerbose(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        MovieMagic.VERBOSE = True

class FileSplit(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        MovieMagic.FILE_SPLIT = values

class MovieMagic:
    DIRECTORY_LIST      = []
    FILE_LIST           = []
    FILE_SPLIT          = ", *\n|, *\r\n|\n|\r\n"
    OUTPUT_FILE_DIR     = os.getcwd()
    MOVIE_LIST          = []
    SUBMISSION_URL_LIST = []
    RESULTS             = {}
    VERBOSE             = True

    @staticmethod
    def parse_directories():
        movie_list = []
        for directory in MovieMagic.DIRECTORY_LIST:
            for ext in EXTENSIONS:
                movie_list.extend([os.path.basename(fp) for fp in glob.glob(os.path.join(directory, "*.%s" % ext))])
        MovieMagic.clean_and_add_movie_names(movie_list)

    @staticmethod
    def parse_files():
        for file_path in MovieMagic.FILE_LIST:
            with open(file_path, 'r') as fin:
                buff = fin.read()
            movie_list = re.split(MovieMagic.FILE_SPLIT, buff)
            MovieMagic.clean_and_add_movie_names(movie_list)

    @staticmethod
    def clean_and_add_movie_names(movie_list):
        pattern = '\.' + '|\.'.join(EXTENSIONS) + "|[^a-zA-Z0-9 ]"
        for idx, movie in enumerate(movie_list):
            movie_list[idx] = re.sub(pattern, "", movie).replace('_', ' ').lower()
        if MovieMagic.VERBOSE:
            pprint.pprint(sorted(movie_list))
        MovieMagic.MOVIE_LIST.extend(movie_list)

    @staticmethod
    def create_submission_url_list():
        for movie in MovieMagic.MOVIE_LIST:
            url_list = [OMD_URL + "+".join(re.split(" +", movie))]
            for st, alt in ALTERNATE_TITLES.items():
                if st in movie:
                    m = movie.replace(st, alt)
                    url_list.append(OMD_URL + "+".join(re.split(" +", m)))
            if MovieMagic.VERBOSE:
                print(movie, "\n\t*", "\n\t* ".join(url_list))
            MovieMagic.SUBMISSION_URL_LIST.append( (movie, url_list) )

    @staticmethod
    def submit_urls():
        for movie, url_list in MovieMagic.SUBMISSION_URL_LIST:
            for url in url_list:
                try:
                    if MovieMagic.VERBOSE:
                        print("Submitting Movie(%s) with URL(%s)" % (movie, url))
                    with urllib.request.urlopen(url) as fin:
                        response = json.loads(fin.read().decode('utf-8'))
                        if response.get("Response","") == "False" or response.get("Error","") == "Movie not found!":
                            continue
                        else:
                            MovieMagic.RESULTS[movie] = response
                            break
                except ValueError:
                    pass
                except Exception:
                    traceback.print_exc()

    @staticmethod
    def store_results_raw():
        try:
            with open(os.path.join(MovieMagic.OUTPUT_FILE_DIR, RESULTS_RAW), 'w') as fout:
                fout.write(json.dumps(MovieMagic.RESULTS))
        except Exception as e:
            print(e)
        finally:
            if MovieMagic.VERBOSE:
                pprint.pprint(MovieMagic.RESULTS)

    @staticmethod
    def store_results():
        data            = MovieMagic.RESULTS
        if not data:
            try:
                with open(os.path.join(MovieMagic.OUTPUT_FILE_DIR, RESULTS_RAW), 'r') as fin:
                    data = json.loads(fin.read())
            except Exception as e:
                print(e)
        sorted_results  = []
        for title, movie in data.items():
            #movie = json.loads(movie)
            ratings = []
            for rating in movie.get("Ratings", []):
                r = rating["Value"]
                if "/10" in r:
                    ratings.append(eval(r))
                elif "%%" in r:
                    ratings.append(int(r.replace("%%", "")))
            else:
                if ratings:
                    sorted_results.append((sum(ratings) * 100 / len(ratings), title))
                else:
                    sorted_results.append((0, title))
        sorted_results.sort(key=lambda x: x[0])
        result_str = "\n".join(["% 3d - %s" % (v, t) for v, t in sorted_results[::-1]])
        if MovieMagic.VERBOSE:
            print(result_str)
        with open(os.path.join(MovieMagic.OUTPUT_FILE_DIR, RESULTS_FN), 'w') as fout:
            fout.write(result_str)

    @staticmethod
    def run():
        MovieMagic.parse_directories()
        MovieMagic.parse_files()
        MovieMagic.create_submission_url_list()
        MovieMagic.submit_urls()
        MovieMagic.store_results_raw()
        MovieMagic.store_results()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--directory",    type=str,   action=DirectoryValidation, nargs="+")
    parser.add_argument("-f", "--file",         type=str,   action=FileValidation,      nargs="+")
    parser.add_argument("-s", "--file_split",   type=str,   action=FileSplit,           default=MovieMagic.FILE_SPLIT, help="regex splitter for files")
    parser.add_argument("-o", "--output_dir",   type=str,   action=OutputValidation)
    parser.add_argument("-v", "--verbose",                  action=SetVerbose,          nargs=0)
    parser.parse_args()
    MovieMagic.run()


if __name__ == "__main__":
    main()
