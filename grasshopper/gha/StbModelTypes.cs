using System;
using System.Collections.Generic;
using System.Globalization;
using Rhino.Geometry;

namespace StbGrasshopper
{
    public sealed class StbMaterialModel
    {
        public string Name { get; set; } = "MAT";
        public double E { get; set; } = 205000.0;
        public double G { get; set; } = 79000.0;
        public double Gamma { get; set; } = 78.5;
        public double Alpha { get; set; }
        public double Fy { get; set; } = 235.0;

        public StbMaterialModel Duplicate()
        {
            return new StbMaterialModel
            {
                Name = Name,
                E = E,
                G = G,
                Gamma = Gamma,
                Alpha = Alpha,
                Fy = Fy,
            };
        }

        public bool Matches(StbMaterialModel other, double tolerance)
        {
            if (other == null)
            {
                return false;
            }

            return string.Equals(Name, other.Name, StringComparison.Ordinal)
                && NumbersClose(E, other.E, tolerance)
                && NumbersClose(G, other.G, tolerance)
                && NumbersClose(Gamma, other.Gamma, tolerance)
                && NumbersClose(Alpha, other.Alpha, tolerance)
                && NumbersClose(Fy, other.Fy, tolerance);
        }

        public string ToMateRecord(int id)
        {
            return "MATE,"
                + id
                + ","
                + Name
                + ","
                + StbRecord.Number(E)
                + ","
                + StbRecord.Number(G)
                + ","
                + StbRecord.Number(Gamma)
                + ","
                + StbRecord.Number(Alpha)
                + ","
                + StbRecord.Number(Fy);
        }

        public override string ToString()
        {
            return Name + " (E=" + StbRecord.Number(E) + ")";
        }

        private static bool NumbersClose(double a, double b, double tolerance)
        {
            return Math.Abs(a - b) <= tolerance;
        }
    }

    public sealed class StbSectionModel
    {
        public string Name { get; set; } = "SEC";
        public StbMaterialModel Material { get; set; }
        public int Type { get; set; }
        public List<double> Dimensions { get; } = new List<double>();

        public StbSectionModel Duplicate()
        {
            var copy = new StbSectionModel
            {
                Name = Name,
                Material = Material?.Duplicate(),
                Type = Type,
            };
            copy.Dimensions.AddRange(Dimensions);
            return copy;
        }

        public bool Matches(StbSectionModel other, double tolerance)
        {
            if (other == null)
            {
                return false;
            }

            if (!string.Equals(Name, other.Name, StringComparison.Ordinal) || Type != other.Type)
            {
                return false;
            }

            if (Material == null || other.Material == null)
            {
                return Material == other.Material;
            }

            if (!Material.Matches(other.Material, tolerance))
            {
                return false;
            }

            if (Dimensions.Count != other.Dimensions.Count)
            {
                return false;
            }

            for (var i = 0; i < Dimensions.Count; i++)
            {
                if (Math.Abs(Dimensions[i] - other.Dimensions[i]) > tolerance)
                {
                    return false;
                }
            }

            return true;
        }

        public string ToSectRecord(int id, int materialId)
        {
            var fields = new List<string>
            {
                "SECT",
                id.ToString(CultureInfo.InvariantCulture),
                Name,
                materialId.ToString(CultureInfo.InvariantCulture),
                Type.ToString(CultureInfo.InvariantCulture),
            };

            foreach (var dim in Dimensions)
            {
                fields.Add(StbRecord.Number(dim));
            }

            return string.Join(",", fields);
        }

        public override string ToString()
        {
            return Name + " (type " + Type + ")";
        }
    }

    public sealed class StbElementModel
    {
        public string Name { get; set; } = "ELEM";
        public Line Line { get; set; }
        public StbSectionModel Section { get; set; }
        public double Beta { get; set; }

        public StbElementModel Duplicate()
        {
            return new StbElementModel
            {
                Name = Name,
                Line = Line,
                Section = Section?.Duplicate(),
                Beta = Beta,
            };
        }

        public override string ToString()
        {
            return Name;
        }
    }

    public sealed class StbSupportModel
    {
        public Point3d Point { get; set; }
        public bool Tx { get; set; } = true;
        public bool Ty { get; set; } = true;
        public bool Tz { get; set; } = true;
        public bool Rx { get; set; } = true;
        public bool Ry { get; set; } = true;
        public bool Rz { get; set; } = true;

        public StbSupportModel Duplicate()
        {
            return new StbSupportModel
            {
                Point = Point,
                Tx = Tx,
                Ty = Ty,
                Tz = Tz,
                Rx = Rx,
                Ry = Ry,
                Rz = Rz,
            };
        }

        public string ToConsRecord(int nodeId)
        {
            return "CONS,"
                + nodeId
                + ","
                + Bit(Tx)
                + ","
                + Bit(Ty)
                + ","
                + Bit(Tz)
                + ","
                + Bit(Rx)
                + ","
                + Bit(Ry)
                + ","
                + Bit(Rz);
        }

        public override string ToString()
        {
            return "Support @ " + Point;
        }

        private static int Bit(bool value) => value ? 1 : 0;
    }

    public enum StbLoadKind
    {
        Point,
        Line,
        Area,
    }

    public sealed class StbLoadModel
    {
        public StbLoadKind Kind { get; set; }
        public Point3d Point { get; set; }
        public Line ElementLine { get; set; }
        public List<Line> BoundaryLines { get; } = new List<Line>();
        public int LoadCase { get; set; }
        public Vector3d Force { get; set; }
        public Vector3d Moment { get; set; }
        public bool IsGlobal { get; set; } = true;
        public Vector3d LoadAtI { get; set; }
        public Vector3d LoadAtJ { get; set; }
        public Vector3d Pressure { get; set; }

        public StbLoadModel Duplicate()
        {
            var copy = new StbLoadModel
            {
                Kind = Kind,
                Point = Point,
                ElementLine = ElementLine,
                LoadCase = LoadCase,
                Force = Force,
                Moment = Moment,
                IsGlobal = IsGlobal,
                LoadAtI = LoadAtI,
                LoadAtJ = LoadAtJ,
                Pressure = Pressure,
            };
            copy.BoundaryLines.AddRange(BoundaryLines);
            return copy;
        }

        public string ToPlodRecord(int nodeId)
        {
            return "PLOD,"
                + nodeId
                + ","
                + LoadCase
                + ","
                + StbRecord.Number(Force.X)
                + ","
                + StbRecord.Number(Force.Y)
                + ","
                + StbRecord.Number(Force.Z)
                + ","
                + StbRecord.Number(Moment.X)
                + ","
                + StbRecord.Number(Moment.Y)
                + ","
                + StbRecord.Number(Moment.Z);
        }

        public string ToElodRecord(int elementId, bool reverse)
        {
            var loadAtI = reverse ? LoadAtJ : LoadAtI;
            var loadAtJ = reverse ? LoadAtI : LoadAtJ;
            return "ELOD,"
                + elementId
                + ","
                + LoadCase
                + ","
                + (IsGlobal ? 1 : 0)
                + ","
                + StbRecord.Number(loadAtI.X)
                + ","
                + StbRecord.Number(loadAtI.Y)
                + ","
                + StbRecord.Number(loadAtI.Z)
                + ","
                + StbRecord.Number(loadAtJ.X)
                + ","
                + StbRecord.Number(loadAtJ.Y)
                + ","
                + StbRecord.Number(loadAtJ.Z);
        }

        public string ToAlodRecord(IReadOnlyList<int> elementIds)
        {
            if (elementIds == null || elementIds.Count < 3 || elementIds.Count > 4)
            {
                throw new InvalidOperationException("Area load requires 3 or 4 boundary elements.");
            }

            var fields = new List<string>
            {
                "ALOD",
                LoadCase.ToString(CultureInfo.InvariantCulture),
                StbRecord.Number(Pressure.X),
                StbRecord.Number(Pressure.Y),
                StbRecord.Number(Pressure.Z),
            };
            foreach (var elementId in elementIds)
            {
                fields.Add(elementId.ToString(CultureInfo.InvariantCulture));
            }

            return string.Join(",", fields);
        }

        public override string ToString()
        {
            switch (Kind)
            {
                case StbLoadKind.Line:
                    return "Line load LC" + LoadCase;
                case StbLoadKind.Area:
                    return "Area load LC" + LoadCase;
                default:
                    return "Point load LC" + LoadCase + " @ " + Point;
            }
        }
    }
}
