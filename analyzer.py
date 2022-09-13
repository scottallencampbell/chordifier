import librosa as lr
import librosa.display as lrd
import sys
import numpy as np
from dataclasses import dataclass
import scipy

@dataclass
class Chord:
    tonic: str
    kind: str
    start: float = 0.0
    duration: float = 0.0

hop_length = 512
magnitude_threshold = 0.25
note_names = ['C','C#', 'D','Eb', 'E', 'F', 'F#', 'G', 'G#', 'A', 'Bb', 'B']

major_chord = '100010010000'
minor_chord = '100100010000'
sus2_chord =  '100001010000'
sus4_chord =  '101000010000'
major_7th_chord = '100010010001'
minor_7th_chord = '100100010001'
power_chord = '100000010000'

def short_silences_audio(x,sr,silence_duration_sec=0.1):
    window_length=int((silence_duration_sec/2)*(sr/hop_length)-1)
    if window_length<1:
        window_length=1
    padding=0.5*np.ones((x.shape[0],window_length),dtype=np.float)
    x_aux=np.zeros(x.shape,dtype=np.float)
    x=np.concatenate((padding,x,padding),axis=1)
    for i in range(2*window_length+1):
        x_aux=x_aux+x[:,i:x.shape[1]-2*window_length+i]

    return np.round(x_aux/(2*window_length+1))
    
    

def exp_average(chronogram,hop_length,sr,window_time_sec: np.float=0.5):
    #Using: den = 1+lam+lam^2+....lam^n, and weights wi=(lam^i)/den
    pre_col_exp_average=np.zeros((chronogram.shape[0],1),dtype=np.float)
    k=int(window_time_sec/(hop_length/sr))
    lam=np.exp(-np.log(0.9/0.1+1)/k)#forgeting factor
    den=np.ones((chronogram.shape[0],2),dtype=np.float)
    for j in range(chronogram.shape[1]):
        pre_col_exp_average[:,0]=chronogram[:,j]+lam*pre_col_exp_average[:,0]
        col_exp_average=np.divide(pre_col_exp_average[:,0],den[:,0])
        
        den[chronogram[:,j]>col_exp_average,0]=den[chronogram[:,j]>col_exp_average,1]#Reset denominator to 1 for some elements
        pre_col_exp_average[chronogram[:,j]>col_exp_average,0]=chronogram[chronogram[:,j]>col_exp_average,j]
        chronogram[:,j]=np.divide(pre_col_exp_average[:,0],den[:,0])
        den[:,0]=lam*den[:,0]+1

    return chronogram

def sigmoid_mask(x: float,threshold: float=0, witdh: float=1):
    #With default values, the function is near 0 at 0 and near 1 at 1
    y=8*x/witdh-4-8*threshold/witdh
    sigmoid_mask=np.zeros(x.shape,dtype=np.float)
    sigmoid_values=1/(1 + np.exp(-y))
    sigmoid_mask[y>-4]=sigmoid_values[y>-4]
    return 1/(1 + np.exp(-y))

def rotate(l, n):
    return l[n:] + l[:n]
    
def build_chord_map(base):
    chord_amp = {}

    for i, note in enumerate(note_names):
        chord_in_key = rotate(base, -i)
        chord_amp[chord_in_key] = note
    
    return chord_amp
    
def to_stopwatch(time_in_seconds):
    minutes = time_in_seconds // 60
    seconds = time_in_seconds % 60
    milliseconds = seconds * 1000 % 1000
    return "%02d:%02d.%03d" % (minutes, seconds, milliseconds)

def classify_chord(notes,chroma_binary_col):
    # has to be a power chord at least
    if len(notes) < 2:
        return None, chroma_binary_col

    # get outta here, no jazz chords
    if len(notes) > 6:
        return None, chroma_binary_col
        
    bits = 0
    mask_2=np.zeros((12),dtype=bool)

    for note in list(notes)[:4]:        
        bits = bits + 2 ** (11 - note)
        mask_2[notes]=1

    mask = bin(bits)[2:].zfill(12)
    if mask in major_7th_chords:
        chroma_binary_col[mask_2]=1
        return Chord(major_7th_chords[mask], '7th'),chroma_binary_col
    #elif mask in minor_7th_chords:
    #    return Chord(minor_7th_chords[mask], 'minor 7th')
    elif mask in sus2_chords:
        chroma_binary_col[mask_2]=1
        return Chord(sus2_chords[mask], 'sus2'),chroma_binary_col
    elif mask in sus4_chords:
        chroma_binary_col[mask_2]=1
        return Chord(sus4_chords[mask], 'sus4'),chroma_binary_col
    elif mask in major_chords:
        chroma_binary_col[mask_2]=1
        return Chord(major_chords[mask], 'major'),chroma_binary_col
    elif mask in minor_chords:
        chroma_binary_col[mask_2]=1
        return Chord(minor_chords[mask], 'minor'),chroma_binary_col
    elif mask in power_chords:
        chroma_binary_col[mask_2]=1
        return Chord(power_chords[mask], 'power'),chroma_binary_col
    else:
        return None, chroma_binary_col

def collapse_chord_progression(chords):
    collapsed = [chords[0]]
    
    for i, chord in enumerate(chords[1:]):
        last_chord = chords[i-1]
        
        if chord.tonic == last_chord.tonic and chord.kind == last_chord.kind:
            continue    

        collapsed.append(chord)

     # determine the timespan of each chord    
    for i, chord in enumerate(chords[:-1]):
        next_chord = chords[i+1]
        chord.duration = next_chord.start - chord.start

    return collapsed

def get_raw_chord_progression(chroma, sr, chroma_exp_a, max_reference: np.float = 1):
    chroma_filtered_magnitude=np.zeros(chroma.shape, dtype=np.float32)
    chroma_binary=np.zeros(chroma.shape, dtype=np.float32)
    chords = []
    chords_aux = []
    from_sec = 0
    to_sec = len(chroma[0]) * hop_length / sr
    last_chord = Chord('', '')
    from_segment = int(from_sec * sr / hop_length)
    to_segment = int(to_sec * sr / hop_length)
    magnitudes = chroma[:, 100]
    sorted_notes = sorted(range(len(magnitudes)), key=lambda i: -magnitudes[i])
    sorted_magnitudes = []
    for i, note in enumerate(note_names):
        sorted_magnitudes.append(magnitudes[sorted_notes[i]])

    #print(sorted_magnitudes)
    for segment in range(from_segment, to_segment):
        magnitudes = chroma[:, segment]
        magnitudes_exp_a = chroma_exp_a[:, segment]
        sorted_notes = sorted(range(len(magnitudes)), key=lambda i: -magnitudes[i])
        sorted_magnitudes = []
        sorted_magnitudes_exp_a = []
        notes = []

        # build an array of the hightest magnitudes
        for i, note in enumerate(note_names):
            sorted_magnitudes.append(magnitudes[sorted_notes[i]])
            sorted_magnitudes_exp_a.append(magnitudes_exp_a[sorted_notes[i]])
            
        # build an array of notes above the given magnitude threshold
        for i, note in enumerate(note_names):
            if (sorted_magnitudes_exp_a[i]>magnitude_threshold * max_reference)and(sorted_magnitudes[i]>0):
                notes.append(sorted_notes[i])
                chroma_filtered_magnitude[sorted_notes[i],segment]=sorted_magnitudes[i]
            elif(i>=2)and(sorted_magnitudes_exp_a[i]>0.5*sorted_magnitudes_exp_a[i-1]):
                notes.append(sorted_notes[i])
                chroma_filtered_magnitude[sorted_notes[i],segment] = sorted_magnitudes[i]
            else:
                break
        chord,chroma_binary[:,segment] = classify_chord(notes,chroma_binary[:,segment])
        chords_aux.append(chord)

    chroma_binary=short_silences_audio(chroma_binary,sr,silence_duration_sec=0.1)

    for index_ch, ch in enumerate(chords_aux):
        if np.max(chroma_binary[:,index_ch])==True:
            if (ch != None) and not (last_chord.tonic == ch.tonic and last_chord.kind == ch.kind):
                ch.start = round((index_ch * hop_length / sr), 3)
                chords.append(ch)
                last_chord = ch
                last_chroma_binary=chroma_binary[:,index_ch]

    collapsed = collapse_chord_progression(chords)

    return collapsed, chroma_filtered_magnitude,chroma_binary

def refine_chord_progression(chords):
    refined = []

    for i, chord in enumerate(chords[:-1]):
        next_chord = chords[i+1]
        
        # remove any short 7ths that come before longer majors
        if chord.tonic == next_chord.tonic and chord.kind == '7th' and next_chord.kind == 'major' and chord.duration < next_chord.duration:
            continue

        # remove any short minor 7ths that come before longer minors
        if chord.tonic == next_chord.tonic and chord.kind == 'minor 7th' and next_chord.kind == 'minor' and chord.duration < next_chord.duration:
            continue
            
        refined.append(chord)

    collapsed = collapse_chord_progression(refined)
    return collapsed

def analyze(audio_path):
    samples_average=9
    y, sr = lr.load(audio_path)
    # split track into harmonic and percussive in order to isolate true tonal frequencies
    y_harm, y_perc = lr.effects.hpss(y)
    # add margin to ^^^^
    # add filters?

    # cqt seems to work better than fourier
    chroma_cq = lr.feature.chroma_cqt(y=y_harm, sr=sr, hop_length=hop_length,norm=None)

    #Filtering outliers.
    chroma_cq = np.minimum(chroma_cq,
                    lr.decompose.nn_filter(chroma_cq,aggregate=np.median,
                                                       metric='cosine'))
    
    #Exponential average.
    chroma_cq_exp_a=exp_average(chroma_cq.copy(),hop_length=hop_length,sr=sr,window_time_sec=1)
    
    #Mask implementation using as input Exponential average
    chroma_cq=np.multiply(chroma_cq,sigmoid_mask(chroma_cq_exp_a,threshold=np.max(chroma_cq)*0.1,witdh=np.max(chroma_cq)*0.1))
    
    chroma_cq_exp_a=np.multiply(chroma_cq_exp_a,sigmoid_mask(chroma_cq_exp_a,threshold=np.max(chroma_cq)*0.1,witdh=np.max(chroma_cq)*0.1))
    chroma_cq_exp_a=chroma_cq_exp_a/np.amax(chroma_cq_exp_a,axis=0)
    
    chroma_smooth = scipy.ndimage.median_filter(chroma_cq, size=(1, samples_average))
    chroma_smooth = chroma_smooth/np.amax(chroma_smooth,axis=0)
        
    #lr.display.specshow(chroma_cq, y_axis='chroma', x_axis='time')

    raw,chroma_filtered_magnitude,chroma_binary = get_raw_chord_progression(chroma_smooth, sr,chroma_cq_exp_a,max_reference=1)
    refined = refine_chord_progression(raw)
    
    return refined, chroma_cq, chroma_cq_exp_a, chroma_binary

major_chords = build_chord_map(major_chord)
minor_chords = build_chord_map(minor_chord)
major_7th_chords = build_chord_map(major_7th_chord)
minor_7th_chords = build_chord_map(minor_7th_chord)
sus2_chords = build_chord_map(sus2_chord)
sus4_chords = build_chord_map(sus4_chord)
power_chords = build_chord_map(power_chord)
