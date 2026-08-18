using System;
using Grasshopper.Kernel;

namespace StbGrasshopper
{
    internal static class StbAnalyzeCommon
    {
        public static StbAnalyzeResult Run(
            GH_Component component,
            string datPath,
            string pythonExe,
            string repoRoot,
            bool run,
            string outPath,
            int loadCase)
        {
            if (!string.IsNullOrWhiteSpace(datPath))
            {
                datPath = System.IO.Path.GetFullPath(datPath);
            }

            var result = StbProcessRunner.Analyze(
                datPath,
                pythonExe,
                repoRoot,
                run,
                outPath,
                loadCase >= 0 ? (int?)loadCase : null);

            if (!result.Success)
            {
                component.AddRuntimeMessage(GH_RuntimeMessageLevel.Warning, result.Summary);
                if (!string.IsNullOrWhiteSpace(result.Stderr))
                {
                    component.AddRuntimeMessage(GH_RuntimeMessageLevel.Error, result.Stderr);
                }
            }

            return result;
        }

        public static void SetOutputs(
            IGH_DataAccess da,
            StbAnalyzeResult result,
            StbModelModel inputModel,
            string datPath)
        {
            da.SetData(0, result.Success);
            da.SetData(1, result.ExitCode);
            da.SetData(2, result.OutPath);
            da.SetData(3, result.Stdout);
            da.SetData(4, result.Stderr);
            da.SetData(5, result.Summary);
            da.SetData(6, result.Results);
            var outputModel = inputModel?.Duplicate() ?? new StbModelModel();
            outputModel.Results = result.Results;
            outputModel.DatPath = datPath ?? string.Empty;
            da.SetData(7, new StbModelGoo(outputModel));
        }
    }
}
