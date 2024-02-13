import argparse
import os
import time
import sounddevice as sd
import tensorflow as tf
import tensorflow_io as tfio
from scipy.io.wavfile import write

parser = argparse.ArgumentParser()
parser.add_argument('--device', type=int, default=0)
parser.add_argument("-resolution",type=str,default='int16')
parser.add_argument("-sampling_rate",type=int,default=48000)
parser.add_argument("-no_of_channels",type=int,default=1) # duration of audio

# arguments for get_spectrogram method
parser.add_argument("-downsampling_rate",type=int,default=16000)
parser.add_argument("-frame_length_in_s",type=float,default=0.032)
parser.add_argument("-frame_step_in_s",type=float,default=0.032)
# optimised parameters
parser.add_argument("-dbFSthres",type=int,default=-120)
parser.add_argument("-duration_thres",type=float,default=0.06)

args = parser.parse_args()

def get_audio_from_numpy(indata):
    indata = tf.convert_to_tensor(indata, dtype=tf.float32)
    indata = 2 * ((indata + 32768) / (32767 + 32768)) - 1
    indata = tf.squeeze(indata)
    return indata

def get_spectrogram(numpy_file, sampling_rate=args.sampling_rate,downsampling_rate=args.downsampling_rate, frame_length_in_s=args.frame_length_in_s, frame_step_in_s=args.frame_step_in_s):
    
    if downsampling_rate != sampling_rate:
        sampling_rate_int64 = tf.cast(sampling_rate, tf.int64)
        audio_padded = tfio.audio.resample(numpy_file, sampling_rate_int64, downsampling_rate)

    sampling_rate_float32 = tf.cast(downsampling_rate, tf.float32)
    frame_length = int(frame_length_in_s * sampling_rate_float32)
    frame_step = int(frame_step_in_s * sampling_rate_float32)

    spectrogram = stft = tf.signal.stft(
        audio_padded, 
        frame_length=frame_length,
        frame_step=frame_step,
        fft_length=frame_length
    )
    spectrogram = tf.abs(stft)

    return spectrogram, downsampling_rate

def is_silence(indata):
    spectrogram, sampling_rate = get_spectrogram(indata)

    dbFS = 20 * tf.math.log(spectrogram + 1.e-6)
    energy = tf.math.reduce_mean(dbFS, axis=1)
    non_silence = energy > args.dbFSthres
    non_silence_frames = tf.math.reduce_sum(tf.cast(non_silence, tf.float32))
    non_silence_duration = (non_silence_frames + 1) * args.frame_length_in_s
    if non_silence_duration > args.duration_thres:
        return 0
    else:
        return 1


def callback(indata, frames, callback_time, status):
    indata_num = get_audio_from_numpy(indata)
    flag = is_silence(indata_num)
    if flag==0:
        timestamp = time.time()
        write(f'{timestamp}.wav', args.sampling_rate, indata)
        file_size = os.path.getsize(f'{timestamp}.wav')
        size_in_kb = file_size/1024
        print(f'size: {size_in_kb:.2F}KB file written')



channel = tf.cast(args.no_of_channels, tf.int32)
blocksize = tf.cast(48000, tf.int32)
samplingrate = tf.cast(args.sampling_rate, tf.int64)
with sd.InputStream(device=args.device,blocksize=blocksize, channels=channel,dtype= args.resolution,samplerate=samplingrate, callback=callback):
     while True:
        time.sleep(1)