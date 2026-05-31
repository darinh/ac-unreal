// AcUnrealEditor.Target.cs — editor target. This is what you build to
// open the project in UnrealEditor.exe; this is also the target
// UnrealBuildTool builds in CI to verify the C++ compiles.
using UnrealBuildTool;
using System.Collections.Generic;

public class AcUnrealEditorTarget : TargetRules
{
	public AcUnrealEditorTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Editor;
		DefaultBuildSettings = BuildSettingsVersion.Latest;
		IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
		ExtraModuleNames.Add("AcUnreal");
	}
}
