using System;
using System.Collections.Generic;

namespace StbGrasshopper
{
    internal static class StbSectionDimensions
    {
        private static readonly string[] TypeNames =
        {
            "Rectangle",
            "Circle",
            "I-section",
            "CHS",
            "RHS",
        };

        private static readonly string[][] DimensionNames =
        {
            new[] { "B", "H" },
            new[] { "D" },
            new[] { "H", "B", "tw", "tf" },
            new[] { "D", "t" },
            new[] { "H", "B", "tw", "tf" },
        };

        public static int TypeCount => TypeNames.Length;

        public static string TypeName(int type)
        {
            ValidateType(type);
            return TypeNames[type];
        }

        public static IReadOnlyList<string> ParameterNames(int type)
        {
            ValidateType(type);
            return DimensionNames[type];
        }

        public static int RequiredCount(int type)
        {
            return ParameterNames(type).Count;
        }

        public static IReadOnlyList<double> Defaults(int type)
        {
            switch (type)
            {
                case 0:
                    return new[] { 100.0, 300.0 };
                case 1:
                    return new[] { 100.0 };
                case 2:
                    return new[] { 400.0, 200.0, 8.0, 12.0 };
                case 3:
                    return new[] { 100.0, 5.0 };
                case 4:
                    return new[] { 300.0, 100.0, 5.0, 5.0 };
                default:
                    throw new InvalidOperationException("Unsupported section type: " + type + ".");
            }
        }

        public static string Description(int type)
        {
            switch (type)
            {
                case 0:
                    return "rectangle B, H in mm";
                case 1:
                    return "circle D in mm";
                case 2:
                    return "I-section H, B, tw, tf in mm";
                case 3:
                    return "CHS D, t in mm";
                case 4:
                    return "RHS H, B, t, t in mm";
                default:
                    return "section dimensions in mm";
            }
        }

        private static void ValidateType(int type)
        {
            if (type < 0 || type >= TypeNames.Length)
            {
                throw new InvalidOperationException("Unsupported section type: " + type + ".");
            }
        }

        public static List<double> Resolve(int type, IReadOnlyList<double> dims, bool useDefaultsWhenEmpty)
        {
            var required = RequiredCount(type);
            if (dims == null || dims.Count == 0)
            {
                if (!useDefaultsWhenEmpty)
                {
                    throw new InvalidOperationException(
                        "Section type "
                        + type
                        + " requires "
                        + required
                        + " dimension(s) ("
                        + Description(type)
                        + ").");
                }

                return new List<double>(Defaults(type));
            }

            if (dims.Count != required)
            {
                throw new InvalidOperationException(
                    "Section type "
                    + type
                    + " requires "
                    + required
                    + " dimension(s) ("
                    + Description(type)
                    + "), but "
                    + dims.Count
                    + " value(s) were provided.");
            }

            return new List<double>(dims);
        }
    }
}
