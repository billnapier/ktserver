#!/usr/bin/python

import simplejson as json

import dircache
import os

## Types
MUSIC_ALBUM = "0"
MUSIC_ARTIST = "1"
MUSIC_TRACK = "2"
PHOTO_ALBUM = "3"
PHOTO = "4"
MOVIE_ALBUM = "5"
MOVIE = "6"
PLAYLIST = "7"
GENERIC = "8"
UNKNOWN = "unknown"

MOVIE_EXTENSIONS = [
    "mp4",
    "avi",
    "wmv",
    ]
MUSIC_EXTENSIONS = [
    "mp3",
    "wav",
    "aac",
    ]
PHOTO_EXTENSIONS = [
    "jpg",
    ]

class RootHandler:
    def __init__(self, children):
        self.children_ = children

    def process(self, request):
        cmd = request[1].replace(":", "_")
        if RootHandler.__dict__.has_key(cmd):
            return json.dumps(RootHandler.__dict__[cmd](self, request))

        # Not us, maybe a child
        path = request[2]
        for (k, v) in self.children_.items():
            if path.startswith(k):
                return v.process(request)

        return json.dumps(None)

    def kiwi_getGenericContainerRootsCount(self, request):
        return [[str(len(self.children_.keys()))]]

    def kiwi_getGenericContainerRootsChunk(self, request):
        ids = []
        names = []
        thumbnails = []
        paths = []

        for (k, v) in self.children_.items():
            ids.append(k)
            names.append(os.path.basename(os.path.abspath(k)))
            thumbnails.append(None)
            paths.append(k)

        return [ids, names, thumbnails, paths]

    def utility_ping(self, request):
        return [['pong']]


class Handler:
    def __init__(self, config, mediaDir, mediaUrlFactory):
        self.config_ = config
        self.media_dir_ = mediaDir
        self.media_url_factory_ = mediaUrlFactory

    def process(self, request):
        cmd = request[1].replace(":", "_")
        if Handler.__dict__.has_key(cmd):
            return json.dumps(Handler.__dict__[cmd](self, request))
        return json.dumps(None)

    def kiwi_getPhotosContainerHierarchicalChunk(self, request):
        dirs = self._getChunksHelper(request[2], request[3], request[4])
        # ids, types, names, thumbs, movieUrl, photoUrl???, fullPaths, ???, ???, ???

        empty = []
        types = []
        movieUrls = []
        unk = []
        full_dirs = []
        short_dirs = []
        thumbnails = []
        for (item, fullpath, t) in dirs:
            short_dirs.append(item)
            full_dirs.append(fullpath)
            types.append(t)
            if (t == MOVIE):
                movieUrls.append(self.media_url_factory_.create(fullpath))
                unk.append("0")
                thumbnails.append(None)
            elif t == PHOTO:
                # just give it the full URL rather than worrying about
                # thumbs.  It seems fast enough with the images I'm
                # testing with.
                thumbnails.append(self.media_url_factory_.create(fullpath))
                movieUrls.append(None)
                unk.append(None)
            else:
                movieUrls.append(None)
                unk.append(None)
            empty.append(None)

        ids = full_dirs
        names = short_dirs
        paths = short_dirs

        return [ids, types, names, thumbnails, movieUrls, empty, paths, unk, empty, empty]

    def kiwi_getPhotosContainerHierarchicalCount(self, request):
        files = self._listdir(request[2], excluding=[UNKNOWN, MUSIC_TRACK])
        return [[str(len(files))]]

    def kiwi_getPhotosContainerChildContainerCount(self, request):
        path = request[2]
        t = request[3]
        return self._getItemCount(path, t, excluding=[UNKNOWN, MUSIC_TRACK])

    def kiwi_getItemsCountByPrefixInGenericContainer(self, request):
        path = request[2]
        t = request[3]
        return self._getItemCount(path, t, excluding=[UNKNOWN, MUSIC_TRACK])

    def kiwi_getPlaybackItemsCount(self, request):
        dir = request[2]
        count = 0
        for (item, l, t) in self._listdir(dir, excluding=[UNKNOWN, MUSIC_TRACK]):
            if self._isPlayable(t):
                count+=1
        return [[str(count)]]


    def _getChunksHelper(self, path, count, offset):
        dirs = self._listdir(path, excluding=[UNKNOWN, MUSIC_TRACK])

        # slice out the part we need
        if len(dirs) < count:
            count = len(dirs)
        if offset < 0:
            offset = 0
        return dirs[offset:offset+count]


    def _getItemType(self, item):
        """Item type by simple extension search..."""
        if os.path.isdir(item):
            return GENERIC
        (root, ext) = os.path.splitext(item)
        # splitext leaves the .
        ext = ext[1:]
        if ext in MOVIE_EXTENSIONS:
            return MOVIE
        if ext in MUSIC_EXTENSIONS:
            return MUSIC_TRACK
        if ext in PHOTO_EXTENSIONS:
            return PHOTO
        return UNKNOWN

    def _getItemCount(self, dir, type, excluding=[UNKNOWN]):
        count = 0
        for (item, l, t) in self._listdir(dir, excluding):
            if t == type:
                count+=1
        return [[str(count)]]

    def _listdir(self, path, excluding=[UNKNOWN]):
        path = os.path.join(self.media_dir_, path)
        if os.path.isfile(path):
            return [(path, self._getItemType(path))]
        results = []
        for f in dircache.listdir(path):
            # if file starts with ., skip it
            if f.startswith('.'):
                continue
            l = os.path.join(path, f)
            t = self._getItemType(l)
            if t not in excluding:
                results.append((f, l, t))
        return results

    def _isPlayable(self, t):
        return t == MOVIE or t == PHOTO or t == MUSIC_TRACK

    def kiwi_getContainerUrisRotationsChunk(self, request):
        dirs = self._getChunksHelper(request[2], request[3], request[4])

        ids = []
        movieUrls = []
        types = []
        empty = []
        for (item, fullpath, t) in dirs:
            if self._isPlayable(t):
                types.append(t)
                movieUrls.append(self.media_url_factory_.create(fullpath))
                ids.append(item)
                empty.append(None)

        return [ids, movieUrls, empty, types]
