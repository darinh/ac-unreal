// AcUnreal.Target.cs — game target (cooked, runtime-only).
// Editor build uses AcUnrealEditor.Target.cs.
using UnrealBuildTool;
using System.Collections.Generic;

public class AcUnrealTarget : TargetRules
{
	public AcUnrealTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Game;
		DefaultBuildSettings = BuildSettingsVersion.Latest;
		IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
		ExtraModuleNames.Add("AcUnreal");
	}
}
