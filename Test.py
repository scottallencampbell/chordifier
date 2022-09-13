from analyzer import analyze
from pathlib import Path
import librosa as lr
import matplotlib.pyplot as plt
import scipy
import numpy as np

def extract_true_labels(labels_path):
    Labels=[]
    Intervals=[]
    with open(labels_fpath,mode='r') as f:
        for line in f:
            stripped_line=line.strip()
            splitted_line=stripped_line.split()
            Labels.append(splitted_line[1])
            Intervals.append([float(splitted_line[3]),float(splitted_line[5])])

    return Labels, Intervals

def extract_results_chords(chords):
    Labels=[]
    Intervals=[]
    for chord in chords:
        label=chord.tonic+'_'+chord.kind
        Labels.append(label)
        end_interval=chord.start+chord.duration
        Intervals.append([chord.start,end_interval])

    return Labels, Intervals

wav_fpath=Path("audio_data/Guitar Chords", "Guitar Chords.mp3")
chords,chords_chroma,chroma_cq_exp_a,chroma_binary = analyze(str(wav_fpath))

labels_fpath=Path("audio_data/Guitar Chords/Labels.txt")
True_labels, Intervals = extract_true_labels(labels_fpath)
Estimated_labels, Estimated_Intervals = extract_results_chords(chords)

plt.clf()
fig, ax = plt.subplots(nrows=2, sharex=True)

chroma_smooth = scipy.ndimage.median_filter(chords_chroma, size=(1, 9))
chroma_smooth_norm = chroma_smooth/np.amax(chroma_smooth,axis=0)

chords_chroma_img=lr.display.specshow(chroma_smooth_norm, y_axis='chroma', x_axis='time',ax=ax[0],hop_length=512)
chords_chroma_img2=lr.display.specshow(chroma_binary, y_axis='chroma', x_axis='time',ax=ax[1],hop_length=512)
fig.colorbar(chords_chroma_img, ax=ax[0])
fig.colorbar(chords_chroma_img2, ax=ax[1])
ax[0].set(ylabel='Default chroma')
plt.show()
