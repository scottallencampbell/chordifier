from analyzer import analyze
from pathlib import Path
import librosa as lr
import matplotlib.pyplot as plt
import scipy
import numpy as np


#---------------------------Auxiliary-function definitions---------------------------#
#True label extraction using the path for the labels
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

#Results extraction from the analysis
def extract_results_chords(chords):
    Labels=[]
    Intervals=[]
    for chord in chords:
        label=chord.tonic+'_'+chord.kind
        Labels.append(label)
        end_interval=chord.start+chord.duration
        Intervals.append([chord.start,end_interval])

    return Labels, Intervals
#------------------------------------------------------------------------------------#


#Path to audio.
wav_fpath=Path("audio_data/Guitar Chords", "Guitar Chords.mp3")

#Boolean flag for visual representations.
Flag_chron_related_info=True

if Flag_chron_related_info:
    #Set Flag_chron_related_info to True if the information related to the chronogram is desired such as:
    #chords_chroma - Chronogram after being filtered.
    #chroma_binary - Binary visual representation of the identified notes.
    #chroma_filtered_magnitude -  Similar to chroma_binary but using the values of chords_chroma
    #chroma_cq_exp_a - exponentially-average and normalized chronogram, but before some filters and before classification  
    chords,chords_chroma,chroma_binary,chroma_cq_exp_a,chroma_filtered_magnitude = analyze(str(wav_fpath), Flag_chron_related_info = Flag_chron_related_info)

    labels_fpath=Path("audio_data/Guitar Chords/Labels.txt")
    True_labels, Intervals = extract_true_labels(labels_fpath)
    Estimated_labels, Estimated_Intervals = extract_results_chords(chords)

    plt.clf()
    fig, ax = plt.subplots(nrows=2, sharex=True)

    max_val_per_col=np.amax(chords_chroma,axis=0)#Maximum value per colum is computed for normalziation
    max_val_per_col[max_val_per_col==0]=1 #elements equal to 0 are set to 1 for division purposes.
    chords_chroma_norm = chords_chroma/max_val_per_col

    #Visuals linked to chroma
    chords_chroma_img=lr.display.specshow(chords_chroma, y_axis='chroma', x_axis='time',ax=ax[0],hop_length=512)
    chords_chroma_img2=lr.display.specshow(chroma_binary, y_axis='chroma', x_axis='time',ax=ax[1],hop_length=512)
    fig.colorbar(chords_chroma_img, ax=ax[0])
    fig.colorbar(chords_chroma_img2, ax=ax[1])
    ax[0].set(ylabel='Default chroma')
    plt.show()

else:
    chords = analyze(str(wav_fpath), Flag_chron_related_info = Flag_chron_related_info)
    labels_fpath=Path("audio_data/Guitar Chords/Labels.txt")
    True_labels, Intervals = extract_true_labels(labels_fpath)
    Estimated_labels, Estimated_Intervals = extract_results_chords(chords)

