using System.IO.Compression;
using System.Runtime.CompilerServices;
using NativeWeave.Research;

int checks=0;
void Check(bool value) { if (!value) throw new Exception("codec differential failed");checks++; }
byte[] BaselineCompress(byte[] data)
{
    using var output=new MemoryStream();
    using(var z=new ZLibStream(output,CompressionLevel.Optimal,true)) z.Write(data);
    return output.ToArray();
}
byte[] BaselineDecompress(byte[] data)
{
    using var input=new MemoryStream(data);using var z=new ZLibStream(input,CompressionMode.Decompress);
    using var output=new MemoryStream();z.CopyTo(output);return output.ToArray();
}
var random=new Random(182026);
foreach(int size in new[]{0,1,1024,65536,1048576})
{
    var data=new byte[size];random.NextBytes(data);
    var compressed=Codec.Compress(data);
    Check(Codec.Decompress(compressed).AsSpan().SequenceEqual(data));
    Check(BaselineDecompress(compressed).AsSpan().SequenceEqual(data));
    Check(Codec.Decompress(BaselineCompress(data)).AsSpan().SequenceEqual(data));
}
try { Codec.Decompress(new byte[]{0,1,2});throw new Exception("malformed accepted"); }
catch(InvalidDataException) {checks++;}
if(args.Contains("--aot")) Check(!RuntimeFeature.IsDynamicCodeSupported);
Console.WriteLine($"codec checks={checks} aot={!RuntimeFeature.IsDynamicCodeSupported}");
