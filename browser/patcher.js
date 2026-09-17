/* Byte-exact port of the standalone Python transport patcher. No audio decoding APIs. */
'use strict';
(() => {
const R = globalThis.BEATROOTS_RELEASE;
const check = (ok, message) => { if (!ok) throw new Error(message); };
const hex = s => Uint8Array.from(s.match(/../g) || [], x => parseInt(x, 16));
const ascii = s => Uint8Array.from(s, c => c.charCodeAt(0));
const view = a => new DataView(a.buffer, a.byteOffset, a.byteLength);
const equal = (a, b) => a.length === b.length && a.every((x, i) => x === b[i]);
const matches = (a, b, at) => at + b.length <= a.length && b.every((x, i) => x === a[at+i]);
const sum = a => a.reduce((s, x) => s + x, 0);
const join = arrays => { const out = new Uint8Array(arrays.reduce((s,a)=>s+a.length,0)); let p=0; for(const a of arrays){out.set(a,p);p+=a.length;} return out; };
const hash = async a => {
 check(globalThis.crypto?.subtle, 'SHA-256 is unavailable. Open this page in a current browser using HTTPS or localhost.');
 return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',a)),x=>x.toString(16).padStart(2,'0')).join('');
};
function decode(raw) {
 check(raw.length>=12 && matches(raw,ascii('RIFF'),0) && matches(raw,ascii('WAVE'),8),'Expected RIFF/WAVE.');
 check(view(raw).getUint32(4,true)+8===raw.length,'Incorrect RIFF length.');
 const chunks=[]; let p=12;
 while(p<raw.length){
  check(p+8<=raw.length,'Truncated WAV chunk.');
  const size=view(raw).getUint32(p+4,true), end=p+8+size+(size&1);
  check(end<=raw.length,'Truncated WAV chunk.');
  chunks.push({tag:String.fromCharCode(...raw.subarray(p,p+4)),data:raw.subarray(p+8,p+8+size),original:raw.subarray(p,end)});p=end;
 }
 const fmt=chunks.filter(c=>c.tag==='fmt '), aud=chunks.filter(c=>c.tag==='data');
 check(fmt.length===1 && aud.length===1,'Expected one format and audio chunk.');
 check(fmt[0].data.length>=16,'Truncated format.'); const f=view(fmt[0].data);
 check(f.getUint16(0,true)===1 && f.getUint16(2,true)===1 && f.getUint32(4,true)===44100 && f.getUint32(8,true)===88200 && f.getUint16(12,true)===2 && f.getUint16(14,true)===16,'Expected mono 16-bit PCM at 44100 Hz.');
 const audio=aud[0].data; check(audio.length>=60,'Missing update stream.');
 const one=audio.subarray(0,20);p=0;while(matches(audio,one,p))p+=20;
 const zero=audio.subarray(p,p+40);check(p>=2000 && zero.length===40 && !matches(zero,one,0),'Invalid tone leader.');
 for(const wave of [zero,one]){const half=wave.length/4, v=view(wave), sign=v.getInt16(0,true)>=0;for(let i=0;i<half*2;i++)check((v.getInt16(i*2,true)>=0)===(i<half?sign:!sign),'Unexpected waveform.');}
 const storage=new Uint8Array(Math.ceil(audio.length/20));let n=0;p=0;
 while(p<audio.length){if(matches(audio,one,p)){storage[n++]=1;p+=20;}else if(matches(audio,zero,p)){storage[n++]=0;p+=40;}else throw new Error('Unrecognized waveform at byte '+p);}
 return {chunks,bits:storage.subarray(0,n),waves:[zero,one]};
}
function read(bits,p,n){check(p>=0 && p+n*8<=bits.length,'Truncated transport.');const a=new Uint8Array(n);for(let i=0;i<n;i++)for(let j=0;j<8;j++)a[i]|=bits[p+i*8+j]<<j;return a;}
function write(bits,p,a){check(p>=0 && p+a.length*8<=bits.length,'Patch outside transport.');for(const x of a)for(let j=0;j<8;j++)bits[p++]=(x>>j)&1;}
function footer(image){const a=new Uint8Array(64),v=view(a);for(let i=0;i<32;i++){let crc=65535;for(const x of image.subarray(i*1024,(i+1)*1024)){crc^=x;for(let j=0;j<8;j++)crc=(crc>>>1)^((crc&1)?0x8408:0);}v.setUint16(i*2,crc,true);}return a;}
function wordSum(a){let s=0,v=view(a);for(let i=0;i<a.length;i+=2)s+=v.getUint16(i,true);return s&65535;}
function validate(bits){
 let leader=0;while(leader<bits.length && bits[leader])leader++;
 check(leader>=100 && read(bits,leader+1,1)[0]===169,'Missing header marker.');
 const h=read(bits,leader+9,33);
 check(equal(h.subarray(0,16),ascii('KORG SYSTEM FILE')),'Missing Korg header.');
 check((sum(h.subarray(0,32))&255)===h[32],'Header checksum failed.');
 check(equal(h.subarray(16,24),hex('a82f00ff00ff0104')) && h.subarray(24,32).every(x=>x===0),'Expected Beats SYS 1.04.');
 let p=leader+9+264,footerOffset;const offsets=[],image=new Uint8Array(32768);
 for(let i=0;i<129;i++){
  const gap=i===0?4000:350;check(p+gap<bits.length && bits.subarray(p,p+gap).every(x=>x===1) && bits[p+gap]===0,'Packet gap failed.');p+=gap+1;
  check(read(bits,p,1)[0]===169,'Packet marker failed.');p+=8;
  if(i<128){const packet=read(bits,p,260);check(packet.subarray(256,259).every(x=>x===85),'Packet trailer failed.');check((sum(packet.subarray(0,256))&255)===packet[259],'Packet checksum failed.');offsets.push(p);image.set(packet.subarray(0,256),i*256);p+=2080;}
  else {footerOffset=p;const packet=read(bits,p,65);check((sum(packet.subarray(0,64))&255)===packet[64],'Footer checksum failed.');check(equal(packet.subarray(0,64),footer(image)),'Firmware CRC failed.');p+=520;}
 }
 check(wordSum(image)===0,'Internal firmware checksum failed.');check(bits.subarray(p).every(x=>x===1),'Unexpected trailing data.');return {image,offsets,footerOffset};
}
const tick = () => new Promise(resolve=>setTimeout(resolve,0));
async function build(raw,progress=()=>{}){
 progress('Checking official firmware…');await tick();
 check(raw.length===R.STOCK_WAV_SIZE && await hash(raw)===R.STOCK_WAV_SHA256,'Choose the unmodified volcabeats_sys_0104.wav from Korg’s 1.04 ZIP. Converted, damaged or already-patched files cannot be used.');
 progress('Decoding and checking transport…');await tick();const {chunks,bits,waves}=decode(raw),{image,offsets,footerOffset}=validate(bits);
 check(await hash(image)===R.STOCK_SYS_SHA256,'Unexpected firmware image.');
 const patched=image.slice();let end=512;
 for(const [offset,data] of R.PATCHES){const bytes=hex(data);check(offset>=end && offset+bytes.length<=patched.length,'Invalid patch layout.');patched.set(bytes,offset);end=offset+bytes.length;}
 patched[510]=patched[511]=0;view(patched).setUint16(510,(-wordSum(patched))&65535,true);
 check(await hash(patched)===R.PATCHED_SYS_SHA256,'Patched firmware differs from verified release.');
 progress('Building firmware WAV…');await tick();
 offsets.forEach((offset,i)=>{const payload=patched.subarray(i*256,(i+1)*256);write(bits,offset,join([payload,Uint8Array.of(85,85,85,sum(payload)&255)]));});
 const crc=footer(patched);write(bits,footerOffset,join([crc,Uint8Array.of(sum(crc)&255)]));
 let length=0;for(const bit of bits)length+=waves[bit].length;
 const audio=new Uint8Array(length);let p=0;for(const bit of bits){audio.set(waves[bit],p);p+=waves[bit].length;}
 const parts=chunks.map(c=>{if(c.tag!=='data')return c.original;const a=new Uint8Array(8+audio.length+(audio.length&1));a.set(ascii('data'));view(a).setUint32(4,audio.length,true);a.set(audio,8);return a;});
 const body=join([ascii('WAVE'),...parts]),head=new Uint8Array(8);head.set(ascii('RIFF'));view(head).setUint32(4,body.length,true);const result=join([head,body]);
 progress('Verifying the finished WAV…');await tick();
 check(equal(validate(decode(result).bits).image,patched),'Finished WAV failed round-trip verification.');
 check(await hash(result)===R.OUTPUT_WAV_SHA256,'Finished WAV differs from verified release.');return result;
}
globalThis.BeatRoots={build,decode,validate,hash};
})();
