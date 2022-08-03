var wavesurfer = Object.create(WaveSurfer);
var uploadpath = '/uploads';
var duration = 0;
var reelLength = 0;
var reelPixelsPerSecond = 250;
var initialReelOffset = 50;
var lastChordIndex = 0;
var lastChordStart = 0;
var skipLength = 2;
var watchReelInterval;
var $reel;

$(document).ready(function () {

    Dropzone.options.dropzone = {
        paramName: 'file',
        maxFilesize: 100,
        maxFiles: 1,
        uploadMultiple: false,
        addRemoveLinks: true,
        acceptedFiles: 'audio/wav,audio/mpeg,audio/mp3',
        dictDefaultMessage: 'Drop a wav or mp3 file here, or click to browse.',
        accept: function (file, done) {
            done();
        },
        init: function () {
            this.on('success', function (file) {
                receiveFile(file);
            });

            this.on('removedfile', function (file) {
                deleteFile(file);
            });
        }
    };

    $('#controls button').each(function () {
       
        $(this).click(function() {
            let action = $(this).data('action');

            switch (action) {
                case 'play': startReel(); break;
                case 'pause': pauseReel(); break;                   
                case 'back': rewindReel(); break;
                case 'forward': advanceReel(); break;
            }
        });    
    });

    wavesurfer = WaveSurfer.create({
        container: '#waveform',
        waveColor: '#E633BF',
        progressColor: '#651863',
        skipLength: skipLength,
        interact: false
    });

    wavesurfer.on('ready', function() {
        duration = wavesurfer.getDuration();
        reelLength = duration * reelPixelsPerSecond;
    });

    wavesurfer.on('finish', function () {
        setTimeout(resetReel, 1000);
    });

    $reel = $('#reel');

    $('html').delay(1000).fadeIn();
});

const receiveFile = (file) => {
    $('#filename').val(file.name);
    $('button#enchordify').delay(500).fadeIn();
}

const deleteFile = (file) => {
    $('button#enchordify').fadeOut();
}

const enchordify = () => {    
    let file = $('#filename').val();    

    $('button#enchordify').delay(250).fadeOut();
    $('.dropzone .dz-preview').delay(500).fadeOut();
    setTimeout(function() { $('.dropzone').addClass('collapsed'); }, 1000);
    $('.working').delay(2000).fadeIn();

    setTimeout(function() { postFileToApi(file); }, 2500);
}

const displayTrack = (file, data) => {
    $('.working').fadeOut();    
    $('#waveform').css('opacity', 0).show(); // wavesurfer won't render if div is hidden
    $('#chords').css('opacity', 0).show();
    
    wavesurfer.load(`${uploadpath}/${file}`);

    $('#waveform').css('opacity', 1);    
    $('#chords').delay(750).css('opacity', 1); 
    $('#controls').delay(1500).fadeIn();

    $(data).each(function() {
        let div = `<div start='${this.start}'><img src='/static/images/chords/highlighted/${this.tonic.replace('#', '^')}-${this.kind}.png'></div>`;
        $reel.append(div);
        $('#current').append(div);        
    });

    $('#reel div').each(function() { 
        $(this).css('left', `${$(this).attr('start') * reelPixelsPerSecond}px`);
    });
}

const handleApiError = (file, data) => {
    resetPage(); 
}

const resetPage = () => {
    Dropzone.forElement('.dropzone').removeAllFiles();
    $('.working').fadeOut();      
    $('.dropzone .dz-preview, .dropzone').delay(2000).fadeIn();
    setTimeout(function() { $('.dropzone').removeClass('collapsed');}, 2250);    
}

const postFileToApi = (file) => {    
    $.ajax({
        url: '/analyze/uploaded',
        type: 'POST',
        data: JSON.stringify({file: file}),
        contentType: 'application/json',
        success: function(data) {
            displayTrack(file, data);
        },
        error: function(data) {         
            handleApiError(file, data);
        }
    });
}

const startReel = () => {
    wavesurfer.playPause();
    let remainingDuration = duration - wavesurfer.getCurrentTime();

    $reel.css({transition: `all ${remainingDuration}s linear`, left: -reelLength });
    $('#controls button#play').hide();
    $('#controls button#pause').show();

    watchReelInterval = setInterval(watchReelForChordChanges, 100);
}

const pauseReel = () => {
    wavesurfer.playPause();
    $reel.css('left', $reel.css('left'));  
    $('#controls button#pause').hide();
    $('#controls button#play').show();

    clearInterval(watchReelInterval);
}

const rewindReel = () => { 
    let isPlaying = wavesurfer.isPlaying();
    let currentTime = wavesurfer.getCurrentTime();
    
    if (currentTime < skipLength) {    
        wavesurfer.seekTo(0);
    } else {
        wavesurfer.skipBackward();
    }
    
    updateReelTargetPosition(isPlaying);
    resetCurrentChordList();
}

const advanceReel = () => { 
    let isPlaying = wavesurfer.isPlaying();
    let currentTime = wavesurfer.getCurrentTime();
   
    if (currentTime + skipLength > duration) {
        isPlaying = false;
        wavesurfer.seekTo(1);
    } else {
        wavesurfer.skipForward();
    }
    
    if (!isPlaying) { wavesurfer.pause(); }

    updateReelTargetPosition(isPlaying);
    resetCurrentChordList();
}

const resetReel = () => {
    wavesurfer.seekTo(0);
    clearInterval(watchReelInterval);

    $('#controls button#pause').hide();
    $('#controls button#play').show();

    $reel.css('transition', 'none');
    $reel.css('left', initialReelOffset);
    
    $('#current div').attr({class: '', style: ''});

    lastChordIndex = 0;
    lastChordStart = 0;
}

const updateReelTargetPosition = (withAnimation) => { 
    let currentTime = wavesurfer.getCurrentTime();
    let remainingDuration = duration - currentTime;
    let position = initialReelOffset - currentTime * reelPixelsPerSecond;
    
    $reel.css({transition: `all 0s linear`, left: position + 'px' }); // first transition stop

    if (withAnimation) { // the transition doesn't reset directly unless the first transition stop executes completely
        setTimeout(function() {
            $reel.css({transition: `all ${remainingDuration}s linear`, left: -reelLength + 'px' });
        }, 1);
    }
}

const watchReelForChordChanges = () => {
    let $nextChord = $($('#reel div')[lastChordIndex]);
    let nextChordStart = $nextChord.attr('start');
    let now = wavesurfer.getCurrentTime();
   
    if (now > nextChordStart) {
        updateCurrentChord(lastChordIndex);

        lastChordIndex++;
        lastChordStart = nextChordStart;
    }
}

const updateCurrentChord = (index) => {
    let $currents = $('#chords #current div');

    if (index > 0) {
        $($currents[index - 1]).addClass('no-transition').css({opacity: 0});
    }

    $($currents[index]).addClass('active');
    setTimeout(function() { $($currents[index]).addClass('decay'); }, 100);
}

const resetCurrentChordList = () => {
    let currentTime = wavesurfer.getCurrentTime();
    let $currents = $('#current div');
    let length = $currents.length;
    
    lastChordIndex = -1;

    $currents.each(function(index) {                     
        if (Number($(this).attr('start')) > currentTime) 
            return false;
        else  {
            lastChordIndex = index;
            lastChordStart = $(this).attr('start');
        }
    });

    if (lastChordIndex == -1) { 
        lastChordIndex = 0;
        return; 
    }
    
    $currents.eq(lastChordIndex).attr({class: 'active decay no-transition', style: ''});

    if (lastChordIndex > 0)
        $currents.slice(0, lastChordIndex - 1).attr({class: '', style: 'opacity: 0'});

    if (lastChordIndex < length - 1)
        $currents.slice(lastChordIndex + 1).attr({class: '', style: ''});
}
