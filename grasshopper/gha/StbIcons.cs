using System;
using System.Drawing;
using System.Reflection;

namespace StbGrasshopper
{
    /// <summary>
    /// Loads the 24 x 24 component icons embedded in StbGrasshopper.gha.
    /// Icons are pre-rendered PNG files, so no graphics drawing is performed
    /// when the plug-in runs.
    /// </summary>
    internal static class StbIcons
    {
        public static Bitmap Analyze => AnalyzeIcon.Value;
        public static Bitmap Material => MaterialIcon.Value;
        public static Bitmap Section => SectionIcon.Value;
        public static Bitmap Element => ElementIcon.Value;
        public static Bitmap Support => SupportIcon.Value;
        public static Bitmap Load => LoadIcon.Value;
        public static Bitmap PointLoad => PointLoadIcon.Value;
        public static Bitmap LineLoad => LineLoadIcon.Value;
        public static Bitmap AreaLoad => AreaLoadIcon.Value;
        public static Bitmap Assemble => AssembleIcon.Value;
        public static Bitmap LoadCases => LoadCasesIcon.Value;
        public static Bitmap Displacements => DisplacementsIcon.Value;
        public static Bitmap Forces => ForcesIcon.Value;
        public static Bitmap DeformedShape => DeformedShapeIcon.Value;
        public static Bitmap DatNodes => DatNodesIcon.Value;
        public static Bitmap DatBeams => DatBeamsIcon.Value;
        public static Bitmap LoadContainer => LoadContainerIcon.Value;
        public static Bitmap MaterialContainer => MaterialContainerIcon.Value;
        public static Bitmap SectionContainer => SectionContainerIcon.Value;
        public static Bitmap ModelContainer => ModelContainerIcon.Value;
        public static Bitmap ElementContainer => ElementContainerIcon.Value;
        public static Bitmap SupportContainer => SupportContainerIcon.Value;

        private const string ResourcePrefix = "StbGrasshopper.Resources.Icons.";

        private static readonly Lazy<Bitmap> AnalyzeIcon = Icon("Analyze");
        private static readonly Lazy<Bitmap> MaterialIcon = Icon("Material");
        private static readonly Lazy<Bitmap> SectionIcon = Icon("Section");
        private static readonly Lazy<Bitmap> ElementIcon = Icon("Element");
        private static readonly Lazy<Bitmap> SupportIcon = Icon("Support");
        private static readonly Lazy<Bitmap> LoadIcon = Icon("Load");
        private static readonly Lazy<Bitmap> PointLoadIcon = Icon("PointLoad");
        private static readonly Lazy<Bitmap> LineLoadIcon = Icon("LineLoad");
        private static readonly Lazy<Bitmap> AreaLoadIcon = Icon("AreaLoad");
        private static readonly Lazy<Bitmap> AssembleIcon = Icon("Assemble");
        private static readonly Lazy<Bitmap> LoadCasesIcon = Icon("LoadCases");
        private static readonly Lazy<Bitmap> DisplacementsIcon = Icon("Displacements");
        private static readonly Lazy<Bitmap> ForcesIcon = Icon("Forces");
        private static readonly Lazy<Bitmap> DeformedShapeIcon = Icon("DeformedShape");
        private static readonly Lazy<Bitmap> DatNodesIcon = Icon("DatNodes");
        private static readonly Lazy<Bitmap> DatBeamsIcon = Icon("DatBeams");
        private static readonly Lazy<Bitmap> LoadContainerIcon = Icon("LoadContainer");
        private static readonly Lazy<Bitmap> MaterialContainerIcon = Icon("MaterialContainer");
        private static readonly Lazy<Bitmap> SectionContainerIcon = Icon("SectionContainer");
        private static readonly Lazy<Bitmap> ModelContainerIcon = Icon("ModelContainer");
        private static readonly Lazy<Bitmap> ElementContainerIcon = Icon("ElementContainer");
        private static readonly Lazy<Bitmap> SupportContainerIcon = Icon("SupportContainer");

        private static Lazy<Bitmap> Icon(string name)
        {
            return new Lazy<Bitmap>(() => LoadBitmap(name), true);
        }

        private static Bitmap LoadBitmap(string name)
        {
            var assembly = typeof(StbIcons).GetTypeInfo().Assembly;
            var resourceName = ResourcePrefix + name + ".png";

            using (var stream = assembly.GetManifestResourceStream(resourceName))
            {
                if (stream == null)
                {
                    throw new InvalidOperationException(
                        "Embedded Grasshopper icon was not found: " + resourceName);
                }

                // Clone the decoded image so the manifest stream can be closed.
                using (var decoded = new Bitmap(stream))
                {
                    return new Bitmap(decoded);
                }
            }
        }
    }
}
