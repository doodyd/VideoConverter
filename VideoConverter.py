#!/usr/bin/env python
# coding=utf-8

import os
import sys
import subprocess
import datetime

DEFAULT_VIDEO_CODEC = "copy"
OUTPUT_VIDEO_CODEC = "h264"

DEFAULT_AUDIO_CODEC = "copy"
OUTPUT_AUDIO_CODEC = "aac"

MAX_WIDTH = 854
MAX_HEIGHT = 480

OUT_VLIB = "libx264"
OUT_ALIB = "aac"
OUT_EXTENSION = ".mp4"
MKV_EXTENSION = ".mkv"
TEMP_EXTENSION = ".tmp.mp4"


def main(args, section=None):
	# log file	====================================================================================
	logfilename = os.path.splitext(args[0])[0] + ".log"

	#	ensure file exists
	rv = subprocess.call('/usr/bin/touch "' + logfilename + '"', shell=True)

	#	open for append
	logfile = open(logfilename, "a")

	#	new header
	logfile.write("****************************************************************************\n")
	logfile.write(str(datetime.datetime.now()) + "\n")
	logfile.write("\n")


	# process input file	========================================================================
	infilename = args[1]

	logfile.write("input file: " + infilename + "\n")

	#	ensure input file exists
	if (not os.path.isfile(infilename)):
		logfile.write("<-- input file does not exist; aborting\n")
		
		return 1

	inextension = os.path.splitext(infilename)[-1].lower()
	commandoutput = os.path.splitext(args[0])[0] + ".output"
	
	if os.path.isfile(commandoutput):
		os.remove(commandoutput)

	#	command to extract video stream details
	command = '/usr/local/bin/ffprobe -v error -select_streams v:0 -show_entries stream=width,height,codec_name -of default=noprint_wrappers=1 "' + infilename + '" >"' + commandoutput + '"'
	
	#logfile.write("  command: " + command + "\n")

	rv = subprocess.call(command, shell=True)

	if (not os.path.isfile(commandoutput)):
		logfile.write("<-- no ffprobe(v) output generated; aborting\n")
		
		return 1

	#	fetch command output
	with open(commandoutput) as commandfile:
		lines = commandfile.readlines()

	#	log command output if it failed
	if (rv != 0):
		logfile.writelines(lines)

	#	delete command output
	os.remove(commandoutput)
	
	#	initialise the video properties we need
	invideocodec = ""
	inheight = 0
	inwidth = 0

	#	extract video properties from command output
	for line in lines:
		if (line[:11] == "codec_name="):
			invideocodec = line[11:].lower().rstrip()

		elif (line[:6] == "width="):
			inwidth = int(line[6:].rstrip())

		elif (line[:7] == "height="):
			inheight = int(line[7:].rstrip())


	#	 command to extract audio stream details
	command = '/usr/local/bin/ffprobe -v error -select_streams a:0 -show_entries stream=codec_name -of default=noprint_wrappers=1 "' + infilename + '" >"' + commandoutput + '"'
	
	#logfile.write("  command: " + command + "\n")

	rv = subprocess.call(command, shell=True)

	if (not os.path.isfile(commandoutput)):
		logfile.write("<-- no ffprobe(a) output generated; aborting\n")
		
		return 1
		
	#	fetch command output
	with open(commandoutput) as commandfile:
		lines = commandfile.readlines()
	
	#	log command output if it failed
	if (rv != 0):
		logfile.writelines(lines)

	#	delete command output
	os.remove(commandoutput)

	#	initialise audio properties
	inaudiocodec = ""

	#	extract audio properties from the command output
	for line in lines:
		if (line[:11] == "codec_name="):
			inaudiocodec = line[11:].lower().rstrip()

	#	log input file properties
	logfile.write("  > video codec = " + invideocodec + "; audio codec = " + inaudiocodec + "; dimensions = " + str(inwidth) + "x" + str(inheight) + "\n")

	
	# check what processing is needed	===============================================================
	dotranscode = False
	
	#	initialise output format
	outvideocodec = DEFAULT_VIDEO_CODEC
	outaudiocodec = DEFAULT_AUDIO_CODEC
	outextension = OUT_EXTENSION
	
	if (inextension == OUT_EXTENSION):
		logfile.write("  MP4:\n")

		if (invideocodec != OUTPUT_VIDEO_CODEC):
			logfile.write("    wrong video codec; transcode required\n")
			outvideocodec = OUT_VLIB
			dotranscode = True
			
		if (inaudiocodec != OUTPUT_AUDIO_CODEC):
			logfile.write("    wrong audio codec")

			if (not dotranscode):
				logfile.write("; transcode required")
			
			logfile.write("\n")
		
			outaudiocodec = OUT_ALIB
			dotranscode = True
		
		#	MP4 output will need to go into a temporary file, as input file is the name we want to ultimately end up with
		outextension = TEMP_EXTENSION
		
	elif (inextension == MKV_EXTENSION):
		logfile.write("  MKV: transcode required\n")
		dotranscode = True
		
		if (invideocodec != OUTPUT_VIDEO_CODEC):
			logfile.write("    wrong video codec\n")
			outvideocodec = OUT_VLIB
		
		if (inaudiocodec != OUTPUT_AUDIO_CODEC):
			logfile.write("    wrong audio codec\n")
			outaudiocodec = OUT_ALIB
		
	else:
		logfile.write("  " + inextension[1:].upper() + ": full transcode required\n")
		dotranscode = True
		outvideocodec = OUT_VLIB
		outaudiocodec = OUT_ALIB

	
	#	initialise output dimensions (omit if no change)
	outdimensions = ""
	
	if ((inwidth > MAX_WIDTH) or (inheight > MAX_HEIGHT)):
		logfile.write("  wrong dimensions")
		
		if (not dotranscode):
			logfile.write("; transcode required")
		
		logfile.write("\n")
		
		#	start by using max allowable height and calculating width in original ratio
		outheight = MAX_HEIGHT
		outwidth = int(int(inwidth * MAX_HEIGHT / inheight) / 2) * 2	# ensure even number
		
		#	if width still too big, set max allowable width and calculate height in original ratio
		if (outwidth > MAX_WIDTH):
			outwidth = MAX_WIDTH
			outheight = int(int(inheight * MAX_WIDTH / inwidth) / 2) * 2	# ensure even number
			
		outvideocodec = OUT_VLIB
		outdimensions = " -s " + str(outwidth) + "x" + str(outheight)
		dotranscode = True
		
		logfile.write("    old dimensions: " + str(inwidth) + "x" + str(inheight) + "; new dimensions: " + str(outwidth) + "x" + str(outheight) + "\n")

	
	videooptions = ""
	
	if (outvideocodec != DEFAULT_VIDEO_CODEC):
		videooptions = " -preset fast -crf 22"
		
		
	# exit if no transcoding required	=====================================================================
	if (not dotranscode):
		logfile.write("<-- transcode is not required; exiting\n")
		
		return 0
		
		
	# perform transcode	=====================================================================================
	outfilename = os.path.splitext(infilename)[0] + outextension

	logfile.write("  Output file: " + outfilename + "\n")

	if os.path.isfile(outfilename):
		logfile.write("  Output file exists; deleting")
		os.remove(outfilename)


	#	command to transcode the file
	command = '/usr/local/bin/ffmpeg -i "' + infilename + '" -map 0 -codec:v ' + outvideocodec + videooptions + outdimensions + ' -codec:a ' + outaudiocodec + ' -sn "' + outfilename +'" -hide_banner -loglevel warning >"' + commandoutput + '"'

	logfile.write("  command: " + command + "\n")

	rv = subprocess.call(command, shell=True)

	if ((rv == 0) and os.path.isfile(outfilename)):
		# success status and outfile exists
		logfile.write("  successful conversion; deleting input file\n")

		# delete input file
		os.remove(infilename)

		# if output file needs to become the input file, rename it
		if (inextension == OUT_EXTENSION):
			logfile.write("  renaming " + outfilename + " to " + infilename + "\n")
			os.rename(outfilename, infilename)

		logfile.write("<-- done\n")
	else:
		# error of some kind, write command output to log file
		if (os.path.isfile(commandoutput)):
			with open(commandoutput) as commandfile:
				logfile.writelines(commandfile.readlines())
		
		logfile.write("<-- conversion failed\n")

	if (os.path.isfile(commandoutput)):
		os.remove(commandoutput)
		
	logfile.close()

	return rv


if __name__ == '__main__':
    exit(main(sys.argv))
