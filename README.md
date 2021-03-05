# MUSYSim
Simulator for the early music synthesis programming language: MUSYS.

MUSYS was an early music synthesis language designed by Peter Grogono for EMS in London in the early 1970s for composing and performing electronic music.
More information and links to primary sources are available at https://esolangs.org/wiki/MUSYS

This is an attempt to create a MUSYS simulator to produce text and audio output from MUSYS source code in a way as close as possible to the original EMS software and hardware.

The most detailed source of technical information is the article "MUSYS: Software for an Electronic Music Studio" by Peter Grogono, in _Software — Practice and Experience, 3_, 1973. pp.369-383. [doi:10.1002/spe.4380030410](https://doi.org/10.1002/spe.4380030410)

Additionally [Peter Grogono's blog](http://users.encs.concordia.ca/~grogono/Bio/ems.html) provides good context and history.

The related non-audio language [Mouse](https://esolangs.org/wiki/Mouse) has a relatively 'active' and enthusiastic hobbyist community and new code and interpreters exist for it. I am not aware of any other attempts to resurrect MUSYS.

### Plan

1. Basic parser, operations and flow control - **DONE**
2. Output to STDOUT - **DONE**
3. Test and fix bugs
4. Output compiled device/data pairs for audio (binary / other format?)
5. Converter that takes device instruction output and produces [Nyquist](https://www.cs.cmu.edu/~music/nyquist/) code to synthesise audio


### Conversion to Nyquist

The given MUSYS example of a note with envelope:

    O1 56 A1 12 E1 13 T1 14 E1 7 T1 1
  
converts (roughly) to Nyquist:

    (play (mult (osc 84 0.15) (env 0.14 0 0.01 13 7 7 0.15)))
  
Using my guess of `{Nyquist (MIDI) tone} = {MUSYS tone} + 28`

MUSYS tones range from 0-63. 0 is oscillator off. 32 would be middle C. The scale is apparently 8 octave chromatic, which leaves the highest and lowest notes unreachable. It sounds like there may have been a way to 'tune' an oscillator to reach these though.  
