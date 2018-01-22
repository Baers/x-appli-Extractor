"""
Usage: xappli_extract.py [-vi] [-c | -r] [-y | -n] <output_directory>
       xappli_extract.py --version
       xappli_extract.py -h | --help

Arguments:
    <output_directory>    Where to copy the output

Options:
    -v --verbose            Enable verbose output.
    --version               Show program version.
    -i --ignore_missing     Don't issue warning when a file in the DB is missing on disk
    -y --overwrite          On copy and convert operations, overwrite without prompting
    -n --skip_existing      On copy and convert operations, skip existing files without prompting
    -c --convert            Convert 3gp (MP4 AACLC) files to FLAC (requires ffmpeg)
    -r --rename             Rename 3gp (MP4 AACLC) files to have the extension match the codec (e.g. .aac)

"""
import docopt
import pypyodbc
import tempfile
import subprocess
import os, errno
import sys
import shutil

VERSION='alpha'
#ffmpeg_path = "C:\\Program Files\\ffmpeg\\ffmpeg.exe"
#ffmpeg_cmd = 'ffmpeg -i audio.xxx -c:a flac audio.flac'

NAME_FIELD = 'ObjectName'
OBJECT_TYPE_FIELD = 'ObjectSpecId'
OBJECT_TYPE_MAP = {
    '1': 'Playlist',
    '2': 'File',
    '3': '???',
    '6': 'Special Playlist',
    '8': 'Artist'
}

FIELD_MAP = {
    NAME_FIELD: 'Title',
    '[201]': 'Artist',
    '[202]': 'Coverart Path',
    '[206]': 'Album',
    '[207]': 'Container Type',
    '[208]': 'Codec',
    '[500]': 'Filename'

}

CONVERSION_CONTAINERS = ['MP4', '3gp', 'mp4', '3GP']

CONTAINER_FILETYPE_MAP = {
    'WAV': 'wav',
    'MP3': 'mp3',
    'FLAC': 'flac'
}

CODEC_FILETYPE_MAP = {
    'AACLC': 'aac',
    'MPEG-1 Audio Layer3': 'mp3',
    'MPEG-2 Audio Layer3': 'mp3',
    'FLAC': 'flac'
}

DRM_CONTAINER_MAP = {
    'OpenMG Audio': ['oma','omg']
}

def make_dirs(directory):
    try:
        return os.makedirs(directory)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise 
        return directory

def sanitize_name(path):
    return path.replace(':','').replace('?','').replace('/','').replace('|','').replace('\\','').replace('<', '').replace('>','').replace('*','').replace('"','').replace('＊','')

def main(args):
    #TODO: Ignore missing files option

    output_directory = args['<output_directory>']

    make_dirs(output_directory)  

    db_path = os.path.join(os.getenv("PROGRAMDATA"), "Sony Corporation\\Sony MediaPlayerX\\Packages\\MtData1.mdb") 
    compressed_db_path = os.path.join(os.getenv("PROGRAMDATA"), "Sony Corporation\\Sony MediaPlayerX\\Packages\\MtData.mdb")
  
    with tempfile.TemporaryDirectory() as tmpdirname:

        copied_db = shutil.copy2(db_path, tmpdirname)

        connection = pypyodbc.win_connect_mdb(copied_db)    

        query = "SELECT {} FROM t_object WHERE ObjectSpecId=2".format(",".join(FIELD_MAP.keys()))

        cur = connection.cursor().execute(query)

        for idx, song in enumerate(cur):
            print(idx)

            if song[1] is None:
                artist = "Unknown Artist"
            else:
                artist = song[1]

            if song[3] is None:
                album = "Unknown Album"
            else:
                album = song[3]

            target_dir = os.path.join(output_directory, sanitize_name(artist), sanitize_name(album) )
            #print(target_dir)

            make_dirs(target_dir)
            
            # Copy cover art, if it exists
            # TODO: rename as folder.jpg
            if(song[2] is not None):
                try:
                    shutil.copy2(song[2], target_dir)
                except:
                    pass

            # Copy the audio file
            if song[6] is not None:
                try:
                    copied_file = shutil.copy2(song[6], target_dir)
                except:
                    #TODO: Ignore missing files option
                    copied_file = None
                
                if copied_file is not None:
                    basename, filetype = os.path.splitext(copied_file)
                    if song[4] in CONVERSION_CONTAINERS:
                        target_filetype = "flac"
                        new_filename = "{}.{}".format(basename, target_filetype)
                        new_fullpath = os.path.join(target_dir, new_filename)
                        print("Converting {} to {}".format("{}{}".format(basename, filetype), new_filename))
                        subprocess.call(['ffmpeg', '-loglevel', 'quiet', '-n','-i', copied_file,'-c:a','flac', '-compression_level', '12', new_fullpath])
                        os.remove(copied_file)
            else:
                print("File not found for:")
                print(song)

        connection.close()
    

if __name__ == '__main__':
    ARGS = docopt.docopt(__doc__, version=VERSION, options_first=True)
    sys.exit(main(ARGS))