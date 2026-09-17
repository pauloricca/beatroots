'use strict';
const $=id=>document.getElementById(id);
const file=$('firmware'),patch=$('patch'),audio=$('audio'),play=$('play'),stop=$('stop'),connected=$('connected');
let url=null,busy=false,playing=false;
function reset(){audio.pause();audio.removeAttribute('src');audio.load();if(url)URL.revokeObjectURL(url);url=null;$('result').hidden=true;$('download').removeAttribute('href');connected.checked=false;playing=false;controls();}
function controls(){play.disabled=!url||!connected.checked||playing;stop.disabled=!playing;file.disabled=busy||playing;patch.disabled=busy||playing||!file.files.length;connected.disabled=playing;}
function status(text,error=false){$('status').textContent=text;$('status').classList.toggle('error',error);}
file.addEventListener('change',()=>{reset();status(file.files.length?'Ready to patch '+file.files[0].name+'.':'Waiting for the official WAV.');controls();});
patch.addEventListener('click',async()=>{
 reset();busy=true;controls();
 try{const selected=file.files[0];if(selected.size!==BEATROOTS_RELEASE.STOCK_WAV_SIZE)throw new Error('Wrong file size. Choose the original WAV inside Korg’s System Updater 1.04 ZIP.');
 const bytes=await BeatRoots.build(new Uint8Array(await selected.arrayBuffer()),status);
 url=URL.createObjectURL(new Blob([bytes],{type:'audio/wav'}));audio.src=url;audio.loop=false;audio.playbackRate=1;audio.volume=1;
 $('download').href=url;$('download').download=BEATROOTS_RELEASE.OUTPUT_NAME;$('result').hidden=false;$('play-status').textContent='Playback starts only when you press play.';status('All checks passed. Your patched firmware is ready.');
 }catch(error){reset();status(error.message,true);}finally{busy=false;controls();}
});
connected.addEventListener('change',controls);
play.addEventListener('click',async()=>{if(play.disabled)return;playing=true;controls();audio.currentTime=0;audio.playbackRate=1;audio.loop=false;
 try{await audio.play();$('play-status').textContent='Transferring. Keep this page open and do not interrupt power.';}catch(error){playing=false;controls();$('play-status').textContent='Playback could not start. Try again or download the WAV. '+error.message;}
});
stop.addEventListener('click',()=>{audio.pause();audio.currentTime=0;playing=false;controls();$('play-status').textContent='Transfer interrupted. Prepare the Volca in update mode again before restarting from the beginning.';});
const clock=s=>Number.isFinite(s)?`${Math.floor(s/60)}:${String(Math.floor(s%60)).padStart(2,'0')}`:'—';
function timeline(){$('time').textContent=clock(audio.currentTime)+' / '+clock(audio.duration);$('progress').value=audio.duration?audio.currentTime/audio.duration:0;}
audio.addEventListener('timeupdate',timeline);audio.addEventListener('loadedmetadata',timeline);
audio.addEventListener('ended',()=>{playing=false;controls();$('play-status').textContent='Playback finished. Confirm End on the Volca before switching it off; playback completion alone does not confirm installation.';});
audio.addEventListener('error',()=>{if(!url)return;playing=false;controls();$('play-status').textContent='The browser could not play the WAV. Download it and use an audio player.';});
window.addEventListener('beforeunload',event=>{if(playing){event.preventDefault();event.returnValue='';}});
