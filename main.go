package main

import (
	"log"
	"os"
)

const MaxCode = 4095

type BitWriter struct {
	buffer uint64
	count  int
	output []byte
}

func (w *BitWriter) Write12Bits(n int) {
	n &= 0xFFF

	w.buffer = (w.buffer << 12) | uint64(n)
	w.count += 12

	for w.count >= 8 {
		w.count -= 8

		b := byte(w.buffer >> w.count)
		w.output = append(w.output, b)

		if w.count > 0 {
			w.buffer &= (1 << w.count) - 1
		} else {
			w.buffer = 0
		}
	}
}

func (w *BitWriter) Flush() {
	if w.count > 0 {
		b := byte(w.buffer << (8 - w.count))
		w.output = append(w.output, b)
		w.buffer = 0
		w.count = 0
	}
}

func getCode(s string, dictionary map[string]int) int {
	if len(s) == 1 {
		return int(s[0])
	}

	return dictionary[s]
}

func LZWCompress(input string) []byte {
	if len(input) == 0 {
		return []byte{}
	}

	dictionary := make(map[string]int)

	nextCode := 128
	writer := &BitWriter{}

	current := string(input[0])

	for i := 1; i < len(input); i++ {
		nextChar := string(input[i])
		candidate := current + nextChar

		if _, exists := dictionary[candidate]; exists {
			current = candidate
		} else {
			code := getCode(current, dictionary)
			writer.Write12Bits(code)

			if nextCode <= MaxCode {
				dictionary[candidate] = nextCode
				nextCode++
			}

			current = nextChar
		}
	}

	code := getCode(current, dictionary)
	writer.Write12Bits(code)

	writer.Flush()

	return writer.output
}

func main() {
	file, err := os.ReadFile("./songs/WAV_AREA.wav")
	if err != nil {
		log.Println(err)
		return
	}
	
	compressedBits := LZWCompress(string(file))

	if err := os.WriteFile("output.lzw", compressedBits, 0644); err != nil {
		log.Println(err)
	}
}
