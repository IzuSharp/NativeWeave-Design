using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
internal static partial class BindingConsumer
{
    [LibraryImport("nw_interop_completion_probe",EntryPoint="nw_ic_validate_extent")]
    internal static partial uint Direct(ulong count,ulong width,ulong budget);
    static unsafe void Main(string[] args)
    {
        bool aot=!RuntimeFeature.IsDynamicCodeSupported;
        if(args.Contains("--expect-aot")&&!aot) throw new Exception("Not AOT");
        int cases=0;
        foreach(ulong count in new ulong[]{0,1,64,1UL<<63,ulong.MaxValue})
        foreach(ulong width in new ulong[]{0,1,8,ulong.MaxValue})
        foreach(ulong budget in new ulong[]{0,512,ulong.MaxValue})
        {
            uint direct=Direct(count,width,budget), generated=Generated.Native.nw_ic_validate_extent(count,width,budget);
            if(direct!=generated) throw new Exception("binding disagreement");
            cases++;
        }
        Console.WriteLine($"SUCCESS binding-comparison cases={cases} aot={aot}");
    }
}
