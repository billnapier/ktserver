## Why? ##

The server that comes with the Kodak Theater Player (KTP) is very nice, but it only runs on Windows.  By reverse engineering the protocol, I was able to figure out enough of it to make a small functional version of the server in python.

This project is targeted to run on Mac and Linux, and especially on NAS devices that are running embedded Linux.

## State of the code ##

The code currently supports browsing a number of directories for movie files.  On the KTP, this is under "Pictures and Videos" and then select "Folders".  More support (like photo browsing and music playback) will be forthcoming, but isn't compete yet.

## What will be added ##
  * Photo Browsing
  * Simple Music Support (based on directory layout instead of metadata tag reading)
  * Support for using external webserver to stream media (instead of the bundled one currently used), for performance reasons.

## What probably won't be added ##
  * Anything fancy like "starred" or "timeline" views, unless a neat (simple) was is figured out.
  * Fancy thumbnail support for Video's

## What dependencies do I need to run this ##
  * Python: at least 2.5
  * Twisted: 8.2.0
  * SimpleJSON