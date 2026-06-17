using System;
using Grasshopper.Kernel;
using System.Drawing;

namespace StbGrasshopper
{
    public sealed class StbAnalyzeComponent : GH_Component
    {
        public StbAnalyzeComponent()
            : base(
                "STB Analyze",
                "STB Analyze",
                "Run Structural Toolbox CLI and parse the output file.",
                "STB",
                "Analyze")
        {
        }

        public override Guid ComponentGuid => new Guid("04bd3b60-c622-46f8-8156-afd1f6db5cf5");

        protected override Bitmap Icon => StbIcons.Analyze;

        protected override void RegisterInputParams(GH_InputParamManager pManager)
        {
            pManager.AddTextParameter("DAT Path", "DAT", "Path to the STB .dat file.", GH_ParamAccess.item);
            pManager.AddTextParameter("Python Exe", "Py", "Path to .venv\\Scripts\\python.exe. Leave empty to auto-detect.", GH_ParamAccess.item, string.Empty);
            pManager.AddTextParameter("Repo Root", "Root", "Path to the STB repository root.", GH_ParamAccess.item);
            pManager.AddBooleanParameter("Run", "Run", "Set true to run the solver.", GH_ParamAccess.item, false);
            pManager.AddTextParameter("Out Path", "Out", "Optional .out path. Empty uses the temp folder.", GH_ParamAccess.item, string.Empty);
            pManager.AddIntegerParameter("Load Case", "LC", "Deprecated. Use -1 to keep all load cases in Results.", GH_ParamAccess.item, -1);
        }

        protected override void RegisterOutputParams(GH_OutputParamManager pManager)
        {
            pManager.AddBooleanParameter("Success", "S", "True when the solver returns exit code 0.", GH_ParamAccess.item);
            pManager.AddIntegerParameter("Exit Code", "Code", "STB CLI exit code.", GH_ParamAccess.item);
            pManager.AddTextParameter("Out Path", "Out", "Written .out file path.", GH_ParamAccess.item);
            pManager.AddTextParameter("Stdout", "Stdout", "CLI standard output.", GH_ParamAccess.item);
            pManager.AddTextParameter("Stderr", "Stderr", "CLI standard error.", GH_ParamAccess.item);
            pManager.AddTextParameter("Summary", "Summary", "Short status summary.", GH_ParamAccess.item);
            pManager.AddGenericParameter("Results", "R", "Parsed STB result object.", GH_ParamAccess.item);
        }

        protected override void SolveInstance(IGH_DataAccess da)
        {
            string datPath = null;
            string pythonExe = string.Empty;
            string repoRoot = null;
            bool run = false;
            string outPath = string.Empty;
            int loadCase = -1;

            if (!da.GetData(0, ref datPath)) return;
            da.GetData(1, ref pythonExe);
            if (!da.GetData(2, ref repoRoot)) return;
            da.GetData(3, ref run);
            da.GetData(4, ref outPath);
            da.GetData(5, ref loadCase);

            var result = StbProcessRunner.Analyze(
                datPath,
                pythonExe,
                repoRoot,
                run,
                outPath,
                loadCase >= 0 ? (int?)loadCase : null);

            if (!result.Success)
            {
                AddRuntimeMessage(GH_RuntimeMessageLevel.Warning, result.Summary);
                if (!string.IsNullOrWhiteSpace(result.Stderr))
                {
                    AddRuntimeMessage(GH_RuntimeMessageLevel.Error, result.Stderr);
                }
            }

            da.SetData(0, result.Success);
            da.SetData(1, result.ExitCode);
            da.SetData(2, result.OutPath);
            da.SetData(3, result.Stdout);
            da.SetData(4, result.Stderr);
            da.SetData(5, result.Summary);
            da.SetData(6, result.Results);
        }
    }
}
