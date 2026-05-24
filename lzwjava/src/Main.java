import java.io.*;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.file.*;
import java.util.*;
//This is a rewrite of our python code into Java, to test the efficiency and speed of different languages.
public class Main {

    static final int MAX_CODE = 4095;//2^12-1
    static final int CODE_BITS = 12;//Width of compressed code

    //Read WAV file as bytes and convert those bytes to a string of bits.
    static Object[] wavToBits(String path) throws IOException {
        byte[] fileData = Files.readAllBytes(Paths.get(path));

        StringBuilder allBits = new StringBuilder();
        for (byte b : fileData) {
            allBits.append(String.format("%8s", Integer.toBinaryString(b & 0xFF)).replace(' ', '0'));
        }

        return new Object[]{fileData, allBits.toString()};
    }

    static List<Integer> lzwCompress(String allBits) {
        if (allBits.isEmpty()) return new ArrayList<>();

        Map<String, Integer> dictionary = new HashMap<>();
        List<Integer> compressedBits = new ArrayList<>();

        int prefix = allBits.charAt(0) - '0';
        int nextCode = 2;

        for (int i = 1; i < allBits.length(); i++) {
            int bit = allBits.charAt(i) - '0';
            String candidate = prefix + "," + bit;

            if (dictionary.containsKey(candidate)) {
                prefix = dictionary.get(candidate);
            } else {
                compressedBits.add(prefix);
                if (nextCode <= MAX_CODE) {
                    dictionary.put(candidate, nextCode);
                    nextCode++;
                }

                prefix = bit;
            }
        }
        //Add final prefix
        compressedBits.add(prefix);
        return compressedBits;
    }

    static byte[] compressedBitsToBytes(List<Integer> compressedBits) throws IOException {
        int queue = 0;
        int queueSize = 0;

        ByteArrayOutputStream output = new ByteArrayOutputStream();

        for (int code : compressedBits) {
            //We move current queue bits to the left by 12 bits to empty the space for new compressed bits
            //After shifting apply OR so that we can blend the current queue with the new code
            queue = (queue << CODE_BITS) | (code & 0xFFF);
            queueSize += CODE_BITS;

            while (queueSize >= 8) {
                queueSize -= 8;
                output.write((queue >> queueSize) & 0xFF);
                queue &= (1 << queueSize) - 1;
            }
        }

        if (queueSize > 0) {
            output.write((queue << (8 - queueSize)) & 0xFF);
        }

        ByteBuffer header = ByteBuffer.allocate(4).order(ByteOrder.LITTLE_ENDIAN);
        header.putInt(compressedBits.size());

        ByteArrayOutputStream result = new ByteArrayOutputStream();
        result.write(header.array());
        result.write(output.toByteArray());

        return result.toByteArray();
    }

    static void writeCompressedBytes(byte[] compressedBytes, String path) throws IOException {
        Files.write(Paths.get(path), compressedBytes);
    }

    static void printReport(String wavPath, byte[] wavBytes, String allBits, List<Integer> compressedBits, byte[] compressed, String mp3Path) {
        System.out.println("\n\nLEMPEL-ZIV SONG");
        System.out.println("Group O - Boris Marinković, Janko Kondić, Nikola Gostovikj");

        int wavSize = wavBytes.length;
        int compressedSize = compressed.length;

        System.out.println("\nWAV");
        System.out.println("File: " + wavPath);
        System.out.printf("Size: %,12d bytes%n", wavSize);
        System.out.printf("Bytes were converted to: %,12d bits.%n", allBits.length());
        System.out.printf("Amount of compressed bits (codes) created for the given file: %,12d.%n", compressedBits.size());
        System.out.printf("Compressed size: %,12d bytes%n", compressedSize);
        System.out.printf("Compressed vs Original WAV: %12.4f times%n", (double) compressedSize / wavSize);

        File mp3File = new File(mp3Path);
        if (mp3File.isFile()) {
            long mp3Size = mp3File.length();

            System.out.println("\nMP3");
            System.out.println("File: " + mp3Path);
            System.out.printf("Size: %,12d bytes%n", mp3Size);
            System.out.printf("%nCompressed WAV vs Original MP3: %12.4f times%n", (double) compressedSize / mp3Size);

            if (compressedSize > mp3Size) {
                System.out.printf("LZW output is %.1f times LARGER than MP3.%n", (double) compressedSize / mp3Size);
                System.out.println("Expected: MP3 uses lossy frequency-domain encoding, making it far more efficient than a lossless general-purpose compressor on raw audio.");
            } else {
                System.out.println("LZW output is smaller than MP3.");
                System.out.println("Unexpected: This rarely happens in practice, the audio may be highly repetitive or the MP3 bitrate unusually high.");
            }
        } else {
            System.out.println("\n[ERROR] MP3 file not found at: " + mp3Path + ".");
        }
    }

    public static void main(String[] args) throws IOException {
        String wavPath = "../songs/FIRST_SONG_WAV.wav";
        String mp3Path = "../songs/FIRST_SONG_MP3.mp3";
        String outputPath = "output.lzw";

        if (args.length >= 1) wavPath = args[0];
        if (args.length >= 2) mp3Path = args[1];

        //Read WAV and compress it to bit string
        System.out.println("\nReading WAV file at: " + wavPath + "...");

        if (!new File(wavPath).isFile()) {
            System.out.println("[ERROR] WAV file not found: '" + wavPath + "'.");
            System.exit(1);
        }

        Object[] wavResult = wavToBits(wavPath);
        byte[] fileData = (byte[]) wavResult[0];
        String allBits = (String) wavResult[1];
        System.out.printf(fileData.length+" were read from the WAV file and were converted to "+allBits.length()+" bits");

        System.out.println("\nRunning LZW compression on the converted bits...");
        List<Integer> compressedBits = lzwCompress(allBits);
        System.out.printf(compressedBits.size()+" compressed bits (codes) were created for the given file.");

        byte[] compressedBytes = compressedBitsToBytes(compressedBits);
        System.out.printf("Compressed bits (codes) were packed into "+compressedBytes.length+" bytes.");

        writeCompressedBytes(compressedBytes, outputPath);
        System.out.println("Compressed bytes are saved to: " + outputPath + ".");

        printReport(wavPath, fileData, allBits, compressedBits, compressedBytes, mp3Path);
    }
}