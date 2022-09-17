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

#This function allocates a mask of fixed length around each data point.
#Then an average from the points within the mask is taken and used as new
#value for the point in question. Using this method the value of an element
#become dependent on its closest neighbors and 'sudden' silences or sounds
#are mitigated. 
def short_silences_audio(x,sr,silence_duration_sec=0.1):
    window_length=int((silence_duration_sec/2)*(sr/hop_length)-1)#semi-length (half) of the mask in terms of number of points
    if window_length<1:#Making sure the length of the mask is at least 1
        window_length=1
    padding=0.5*np.ones((x.shape[0],window_length),dtype=np.float)#auxiliary variable for the first and last elements of the time input data 
    x_aux=np.zeros(x.shape,dtype=np.float)#Axuliary variable.
    x=np.concatenate((padding,x,padding),axis=1)#Padded array
    for i in range(2*window_length+1):
        x_aux=x_aux+x[:,i:x.shape[1]-2*window_length+i]#summation of the elements within the mask (different sums for each element)

    return np.round(x_aux/(2*window_length+1)) #The average is return.
    

#This function computes an exponential average for the chronogram using the following reasoning:
# 1. Determine k such that 1+lam+lam^2+....lam^k represents 90% of the value of
#    the sum 1+lam+lam^2+....lam^n.... (up to infinite), considering that k is related to an specific meassure of time.
# 2. Determine lam (forgeting factor) based on 1.
# 3. The average needs to be normalized (using a denominator) to avoid scale bias (1+lam+lam^2+....lam^n.... converges to the value 1/(1-lam))
# 4. Equation in #1 allows for the recurrence relationship exp_average(x[k],x[k-1]..x[0])=(x[k]+lam*exp_average(x[k-1],..x[0]))/den(k)
# 5. The exponential average is reset whenever x[p+])>current exponential average.
def exp_average(chronogram,hop_length,sr,window_time_sec: np.float=0.5):
    #Using: den = 1+lam+lam^2+....lam^n, and weights wi=(lam^i)/den
    pre_col_exp_average=np.zeros((chronogram.shape[0],1),dtype=np.float)
    k=int(window_time_sec/(hop_length/sr))#Determination of the k value linked to 
    lam=np.exp(-np.log(0.9/0.1+1)/k)#forgeting factor
    den=np.ones((chronogram.shape[0],2),dtype=np.float)#The array of normalizers  (denominators) is initialized as 1 (one for each row in the chronogram)
    for j in range(chronogram.shape[1]):
        pre_col_exp_average[:,0]=chronogram[:,j]+lam*pre_col_exp_average[:,0]#auxliary variable computing x[k]+lam*exp_average(x[k-1],..x[0])
        col_exp_average=np.divide(pre_col_exp_average[:,0],den[:,0])
        
        den[chronogram[:,j]>col_exp_average,0]=den[chronogram[:,j]>col_exp_average,1]#Reseting some of denominators to 1 when condition in #5 occurs.  
        pre_col_exp_average[chronogram[:,j]>col_exp_average,0]=chronogram[chronogram[:,j]>col_exp_average,j]#Reseting some of the averages to 0 when condition in #5 occurs.
        chronogram[:,j]=np.divide(pre_col_exp_average[:,0],den[:,0])#Substitution of reset values
        den[:,0]=lam*den[:,0]+1#array of denominators is updated  to fulfill #3

    return chronogram

#This function serves as a simple filter using a sigmoid function with threshold of 0 (simmetry around 2)
def sigmoid_mask(x: float,threshold: float=0, witdh: float=1):
    #With default values, the function is near 0 at 0 and near 1 at 1
    y=8*x/witdh-4-8*threshold/witdh#linear transformation to change the witdh and the threshold of the function)
    sigmoid_mask=np.zeros(x.shape,dtype=np.float)#auxliary array
    sigmoid_values=1/(1 + np.exp(-y))#Sigmoid values
    sigmoid_mask[y>-4]=sigmoid_values[y>-4]#Values below the threshold are discarded to facilitate the use of the returned array in other parts of the code
    return sigmoid_mask

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
    #Initialization (This variable is for debugging and visualization purposes).
    #it will contain the values of the chronogram that passed the classification 
    chroma_filtered_magnitude=np.zeros(chroma.shape, dtype=np.float32)
    chroma_binary=np.zeros(chroma.shape, dtype=np.float32)#Initialization (This variable contains a visual representation of the classfication) 
    chords = []
    chords_aux = []#Initialization of auxliary variable
    from_sec = 0
    to_sec = len(chroma[0]) * hop_length / sr
    last_chord = Chord('', '')
    from_segment = int(from_sec * sr / hop_length)
    to_segment = int(to_sec * sr / hop_length)

    #print(sorted_magnitudes)
    for segment in range(from_segment, to_segment):
        magnitudes = chroma[:, segment]#values of the current segment
        magnitudes_exp_a = chroma_exp_a[:, segment]#values of the current segment after exponential average.
        sorted_notes = sorted(range(len(magnitudes)), key=lambda i: -magnitudes[i])#
        sorted_magnitudes = []#list initialization
        sorted_magnitudes_exp_a = []#List initialization
        notes = []

        # build an array of the hightest magnitudes
        for i, note in enumerate(note_names):
            sorted_magnitudes.append(magnitudes[sorted_notes[i]])
            sorted_magnitudes_exp_a.append(magnitudes_exp_a[sorted_notes[i]])
            
        # build an array of notes fulfilling some conditions
        for i, note in enumerate(note_names):
            #If the value after exp_average is bigger than a percentage of the reference and the value itself is bigger than 0
            if (sorted_magnitudes_exp_a[i]>magnitude_threshold * max_reference)and(sorted_magnitudes[i]>0):
                notes.append(sorted_notes[i])
                chroma_filtered_magnitude[sorted_notes[i],segment]=sorted_magnitudes[i]#The chronogram value of the note is stored
            #If more than 3 notes have been already stored and the current magnitude value after exp_average is at least 50% of the previous value
            elif(i>=2)and(sorted_magnitudes_exp_a[i]>0.5*sorted_magnitudes_exp_a[i-1]):
                notes.append(sorted_notes[i])
                chroma_filtered_magnitude[sorted_notes[i],segment] = sorted_magnitudes[i]#The chronogram value of the note is stored
            #No more checks are neeeded since the values were in non-increasing order.
            else:
                break
        chord,chroma_binary[:,segment] = classify_chord(notes,chroma_binary[:,segment])
        chords_aux.append(chord)

    chroma_binary=short_silences_audio(chroma_binary,sr,silence_duration_sec=0.1)#mitigation of sudden (shorts) silences or sounds
    chroma_filtered_magnitude[chroma_binary==0]=0#Deletion of elements that were also deleted during the short_silences_audio process 

    #Appending classified notes but taking into account the mitigation of sudden silences or sounds.
    #IMPORTANT NOTE: the current process should ideally create new chords and put them in chords_aux, although
    #                the heuristic currently used outside this function does not need it, it should be
    #                considered if the heuristic changes.
    for index_ch, ch in enumerate(chords_aux):
        if np.max(chroma_binary[:,index_ch])==True:#Only if sound (note) hasn't been deleted is considered.
            if (ch != None) and not (last_chord.tonic == ch.tonic and last_chord.kind == ch.kind):
                ch.start = round((index_ch * hop_length / sr), 3)
                chords.append(ch)
                last_chord = ch

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

def analyze(audio_path,Flag_chron_related_info: bool=False):
    samples_average=9
    y, sr = lr.load(audio_path)
    # split track into harmonic and percussive in order to isolate true tonal frequencies
    y_harm, y_perc = lr.effects.hpss(y)
    # add margin to ^^^^
    # add filters?

    # cqt seems to work better than fourier
    chroma_cq = lr.feature.chroma_cqt(y=y_harm, sr=sr, hop_length=hop_length,norm=None)

    #Filtering outliers using similarity metrics of 'patterns' across the whole chroma_cq .
    chroma_cq = np.minimum(chroma_cq,
                    lr.decompose.nn_filter(chroma_cq,aggregate=np.median,
                                                       metric='cosine'))
    
    #Exponential average.
    chroma_cq_exp_a=exp_average(chroma_cq.copy(),hop_length=hop_length,sr=sr,window_time_sec=1)
    
    #Mask implementation using as input chroma_cq and its exponentially averaged values
    chroma_cq=np.multiply(chroma_cq,sigmoid_mask(chroma_cq_exp_a,threshold=np.max(chroma_cq)*0.1,witdh=np.max(chroma_cq)*0.1))

    #Mask implementation using as input exponentially averaged values of chroma_cq
    chroma_cq_exp_a=np.multiply(chroma_cq_exp_a,sigmoid_mask(chroma_cq_exp_a,threshold=np.max(chroma_cq)*0.1,witdh=np.max(chroma_cq)*0.1))
    max_val_per_col=np.amax(chroma_cq_exp_a,axis=0)#Maximum value per colum is computed for normalziation
    max_val_per_col[max_val_per_col==0]=1 #elements equal to 0 are set to 1 for division purposes.
    chroma_cq_exp_a=chroma_cq_exp_a/max_val_per_col#Column-wise normalization with respect to maximum value in column

    #Local row-wise filter applied to further mitigate outliers. 
    chroma_cq = scipy.ndimage.median_filter(chroma_cq, size=(1, samples_average))
    max_val_per_col=np.amax(chroma_cq,axis=0)#Maximum value per colum is computed for normalziation
    max_val_per_col[max_val_per_col==0]=1 #elements equal to 0 are set to 1 for division purposes.
    chroma_cq_norm = chroma_cq/max_val_per_col#Column-wise normalization with respect to maximum value in column
        
    #lr.display.specshow(chroma_cq, y_axis='chroma', x_axis='time')

    raw,chroma_filtered_magnitude,chroma_binary = get_raw_chord_progression(chroma_cq_norm, sr,chroma_cq_exp_a,max_reference=1)
    refined = refine_chord_progression(raw)

    if Flag_chron_related_info:
        return refined, chroma_cq, chroma_binary,chroma_cq_exp_a, chroma_filtered_magnitude
    
    else:
        return refined

major_chords = build_chord_map(major_chord)
minor_chords = build_chord_map(minor_chord)
major_7th_chords = build_chord_map(major_7th_chord)
minor_7th_chords = build_chord_map(minor_7th_chord)
sus2_chords = build_chord_map(sus2_chord)
sus4_chords = build_chord_map(sus4_chord)
power_chords = build_chord_map(power_chord)
