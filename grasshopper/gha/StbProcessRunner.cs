using System;
using System.Diagnostics;
using System.IO;

namespace StbGrasshopper
{
    public static class StbProcessRunner
    {
        public static StbAnalyzeResult Analyze(
            string datPath,
            string pythonExe,
            string repoRoot,
            bool run,
            string outPath,
            int? loadCase = null)
        {
            if (!run)
            {
                return new StbAnalyzeResult
                {
                    Success = false,
                    ExitCode = -1,
                    OutPath = outPath ?? string.Empty,
                    Summary = "run is False; STB was not executed."
                };
            }

            if (string.IsNullOrWhiteSpace(datPath))
            {
                return new StbAnalyzeResult
                {
                    Success = false,
                    ExitCode = 1,
                    Summary = "DAT path is empty. Set STB Assemble Write to true first."
                };
            }

            datPath = Path.GetFullPath(datPath);
            repoRoot = Path.GetFullPath(repoRoot);
            pythonExe = ResolvePythonExe(pythonExe, repoRoot);
            outPath = string.IsNullOrWhiteSpace(outPath) ? DefaultOutputPath(datPath) : Path.GetFullPath(outPath);

            if (!File.Exists(datPath))
            {
                return new StbAnalyzeResult
                {
                    Success = false,
                    ExitCode = 1,
                    OutPath = outPath,
                    Stderr = "Input file not found: " + datPath,
                    Summary = "STB input file was not found."
                };
            }

            Directory.CreateDirectory(Path.GetDirectoryName(outPath));

            var psi = new ProcessStartInfo
            {
                FileName = pythonExe,
                WorkingDirectory = repoRoot,
                Arguments = "-m stb_cli solve " + Quote(datPath) + " -o " + Quote(outPath) + " -q -v",
                UseShellExecute = false,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                CreateNoWindow = true
            };

            using (var process = Process.Start(psi))
            {
                var stdout = process.StandardOutput.ReadToEnd();
                var stderr = process.StandardError.ReadToEnd();
                process.WaitForExit();

                if (process.ExitCode != 0)
                {
                    return new StbAnalyzeResult
                    {
                        Success = false,
                        ExitCode = process.ExitCode,
                        OutPath = outPath,
                        Stdout = stdout,
                        Stderr = stderr,
                        Summary = "STB solve failed with exit code " + process.ExitCode
                    };
                }

                var parsed = StbOutParser.ParseFile(outPath, loadCase);
                StbDatParser.ReadGeometry(datPath, out var nodes, out var elements);
                parsed.DatPath = datPath;
                parsed.Nodes.AddRange(nodes);
                parsed.Elements.AddRange(elements);

                return new StbAnalyzeResult
                {
                    Success = true,
                    ExitCode = process.ExitCode,
                    DatPath = datPath,
                    OutPath = outPath,
                    Stdout = stdout,
                    Stderr = stderr,
                    Results = parsed,
                    Summary =
                        "Solved "
                        + Path.GetFileName(datPath)
                        + "; nodes="
                        + parsed.Nodes.Count
                        + "; elements="
                        + parsed.Elements.Count
                        + "; displacements="
                        + parsed.Displacements.Count
                };
            }
        }

        private static string ResolvePythonExe(string pythonExe, string repoRoot)
        {
            if (!string.IsNullOrWhiteSpace(pythonExe))
            {
                return pythonExe;
            }

            var venvPython = Path.Combine(repoRoot, ".venv", "Scripts", "python.exe");
            return File.Exists(venvPython) ? venvPython : "python";
        }

        private static string DefaultOutputPath(string datPath)
        {
            var outDir = Path.Combine(Path.GetTempPath(), "stb_gh");
            Directory.CreateDirectory(outDir);
            return Path.Combine(outDir, Path.GetFileNameWithoutExtension(datPath) + ".out");
        }

        private static string Quote(string value)
        {
            return "\"" + value.Replace("\"", "\\\"") + "\"";
        }
    }
}
