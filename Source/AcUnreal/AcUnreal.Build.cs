// AcUnreal.Build.cs — primary game module build rules.
//
// CoordCore/* (the pure C++17 coordinate-transform core) lives under
// Public/ and Private/ and is picked up automatically by UBT's file
// scan. The same source files are compiled independently by
// pipeline/coord-transform/build.ps1 for the standalone test rig.
using UnrealBuildTool;

public class AcUnreal : ModuleRules
{
	public AcUnreal(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

		PublicDependencyModuleNames.AddRange(new string[]
		{
			"Core",
			"CoreUObject",
			"Engine",
			"InputCore",
			"EnhancedInput"
		});

		PrivateDependencyModuleNames.AddRange(new string[] { });

		// IWYU enforcement (UE 5.2+ API; the old `bEnforceIWYU = true`
		// was deprecated in 5.2).
		IWYUSupport = IWYUSupport.Full;
	}
}
