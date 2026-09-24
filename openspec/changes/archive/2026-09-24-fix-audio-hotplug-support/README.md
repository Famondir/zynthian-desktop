# fix-audio-hotplug-support

Audio capture/playback ports don't update live when a USB audio interface is reconnected - jackd's ALSA backend is bound to a fixed device at startup, unlike MIDI's a2jmidid which supports real hotplug
