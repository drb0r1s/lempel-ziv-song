import os
import struct
import sys

MAX_CODE = 4095 # The limit of the dictionary: 2^12 - 1.
CODE_BITS = 12 # Each output code is 12 bits.

# Read WAV file as bytes and convert those bytes to a string of bits.
def wavToBits(path: str) -> tuple[bytes, str]:
    file = open(path, "rb") # "rb" stands for "read binary", meaning read byte by byte.

    try:
        fileData = file.read() # fileData contains bytes.
    finally:
        file.close()

    # All bytes from fileData will be converted to 8-bit long bit strings and appended to allBits.
    allBits = "".join(f"{byte:08b}" for byte in fileData)

    return fileData, allBits


def lzwCompress(allBits: str) -> list[int]:
    if not allBits:
        return []

    # Our dictionary is a structure of (example): "aba" -> (compressed bits for "ab", bit for "a").
    dictionary: dict[tuple, int] = {}
    compressedBits: list[int] = []

    prefix = int(allBits[0]) # allBits is a string, so we need to parse it to integer.
    nextCode = 2 # 0 -> 0 and 1 -> 1 are already in the dictionary, so the next free space is 2 -> ?.

    for stringBit in allBits[1:]:
        bit = int(stringBit)
        candidate = (prefix, bit)

        if candidate in dictionary:
            # If candidate was already in the dictionary, we'll use it as a prefix.
            prefix = dictionary[candidate]
        else:
            # Prefix is certainly in the dictionary, so we will add compressed code for prefix, if candidate isn't there.
            compressedBits.append(prefix)

            # We need to add the candidate to the dictionary for the future bits.
            # Also, we need to respet the limit of 2^12 - 1.
            if nextCode <= MAX_CODE:
                dictionary[candidate] = nextCode
                nextCode += 1

            # Our new prefix is exactly where we stopped the compression.
            prefix = bit

    # At the end of the loop, we need to add the final compressed prefix.
    compressedBits.append(prefix)
    return compressedBits


# The LZW compressed data codes are of the size of 12 bits, we need to rearrange them into bytes, for easier decompression.
def compressedBitsToBytes(compressedBits: list[int]) -> bytes:
    queue = 0 # All bits from compressedBits waiting to be rearranged into a byte.
    queueSize = 0

    output = bytearray()

    for code in compressedBits:
        # We move current queue bits to the left by 12 bits, so that we can empty the space for new compressed bits.
        # After shifting, we apply OR so that we can blend the current queue with the new code (compressed bits).
        queue = (queue << CODE_BITS) | (code & 0xFFF)
        queueSize += CODE_BITS

        # When our queue reaches the size of 8, it's ready to be rearranged into a byte.
        while queueSize >= 8:
            queueSize -= 8

            # We need to remove (by shifting right) all the bits that won't be packed into a byte.
            output.append((queue >> queueSize) & 0xFF)

            # All the bits that weren't packed into a byte have to be saved by shifting left the left-over queue size.
            # Let's say we have queueSize = n, then:
            # 1 << n = 0001 00...(followed by n 0s)
            # If we subtract 1 from that we get: 0000 11...(followed by n 1s), which is exactly the number of bits that we want to save.
            queue &= (1 << queueSize) - 1

    # When we're done with the loop, we need to also rearrange all the compressed bits that were left over.
    if queueSize > 0:
        output.append((queue << (8 - queueSize)) & 0xFF)

    # We also need to attach a header so that decompressor would read the data correctly.
    # "<I" means that the least significant byte is stored first (<), and the data type is unsigned integer (4 bytes).
    # Without the header letting the decompressor know how many bits to decompress, there would probably be a garbage at the end, due to zero-padding.
    header = struct.pack("<I", len(compressedBits))

    return bytes(header) + bytes(output)


def writeCompressedBytes(compressedBytes: bytes, path: str) -> None:
    file = open(path, "wb") # "wb" stands for "write binary", meaning write byte by byte.

    try:
        file.write(compressedBytes)
    finally:
        file.close()


def printReport(
    wavPath: str,
    wavBytes: bytes,
    allBits: str,
    compressedBits: list[int],
    compressed: bytes,
    mp3Path: str,
) -> None:
    print("\n\nLEMPEL-ZIV SONG")
    print("Group O - Boris Marinković, Janko Kondić, Nikola Gostovikj")

    wavSize = len(wavBytes)
    compressedSize = len(compressed)

    print("\nWAV")
    print(f"File: {wavPath}")
    print(f"Size: {wavSize:>12,} bytes")
    
    print(f"Bytes were converted to: {len(allBits):>12,} bits.")
    print(f"Amount of compressed bits (codes) created for the given file: {len(compressedBits):>12,}.")
    print(f"Compressed size: {compressedSize:>12,} bytes")
    print(f"Compressed vs Original WAV: {compressedSize / wavSize:>12.4f} times")

    if os.path.isfile(mp3Path):
        mp3Size = os.path.getsize(mp3Path)

        print("\nMP3")
        print(f"File: {mp3Path}")
        print(f"Size: {mp3Size:>12,} bytes")

        print(f"\nCompressed WAV vs Original MP3: {compressedSize / mp3Size:>12.4f} times\n")

        if compressedSize > mp3Size:
            print(f"LZW output is {compressedSize / mp3Size:.1f} times LARGER than MP3.")
            print("Expected: MP3 uses lossy frequency-domain encoding, making it far more efficient than a lossless general-purpose compressor on raw audio.")
        else:
            print("LZW output is smaller than MP3.")
            print("Unexpected: This rarely happens in practice, the audio may be highly repetitive or the MP3 bitrate unusually high.")
    else:
        print(f"\n[ERROR] MP3 file not found at: {mp3Path}.")


def main() -> None:
    # Default paths.
    wavPath = "./songs/FIRST_SONG_WAV.wav"
    mp3Path = "./songs/FIRST_SONG_MP3.mp3"

    outputPath = "output.lzw"

    # First argument: wavPath
    # Second argument: mp3Path
    if len(sys.argv) >= 2:
        wavPath = sys.argv[1]
    if len(sys.argv) >= 3:
        mp3Path = sys.argv[2]

    # Step 1: Read WAV and compress it to bit string (allBits).
    print(f"\nReading WAV file at: {wavPath}...")

    if not os.path.isfile(wavPath):
        print(f"[ERROR] WAV file not found: '{wavPath}'.")
        sys.exit(1)

    fileData, allBits = wavToBits(wavPath)
    print(f"\n{len(fileData):,} bytes were read from the WAV file and were converted to {len(allBits):,} bits.")

    # Step 2: LZW compress.
    print("\nRunning LZW compression on the converted bits...")
    
    compressedBits = lzwCompress(allBits)
    print(f"{len(compressedBits):,} compressed bits (codes) were created for the given file.")

    # Step 3: Rearrange compressed bits into bytes.
    compressedBytes = compressedBitsToBytes(compressedBits)
    print(f"\nCompressed bits (codes) were packed into {len(compressedBytes):,} bytes.")

    # Step 4: write output
    writeCompressedBytes(compressedBytes, outputPath)
    print(f"Compressed bytes are saved to: {outputPath}.")

    # Step 5: report
    printReport(wavPath, fileData, allBits, compressedBits, compressedBytes, mp3Path)


if __name__ == "__main__":
    main()