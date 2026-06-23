using System;
using System.IO;

namespace StbGrasshopper
{
    internal static class StbPathUtil
    {
        public static string DefaultDatPath()
        {
            var temp = Path.GetTempPath();
            if (!string.IsNullOrWhiteSpace(temp))
            {
                return Path.Combine(temp, "stb_grasshopper.dat");
            }

            var appData = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
            if (!string.IsNullOrWhiteSpace(appData))
            {
                return Path.Combine(appData, "stb_grasshopper.dat");
            }

            return Path.Combine(Environment.CurrentDirectory, "stb_grasshopper.dat");
        }

        public static string ResolveDatPath(string path)
        {
            if (string.IsNullOrWhiteSpace(path))
            {
                return DefaultDatPath();
            }

            return Path.GetFullPath(path.Trim());
        }

        public static string WriteTextFile(string path, string text)
        {
            var fullPath = ResolveDatPath(path);
            var directory = Path.GetDirectoryName(fullPath);
            if (!string.IsNullOrWhiteSpace(directory))
            {
                Directory.CreateDirectory(directory);
            }

            File.WriteAllText(fullPath, text);
            return fullPath;
        }
    }
}
