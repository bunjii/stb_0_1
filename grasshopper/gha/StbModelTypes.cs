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

    public sealed class StbLoadModel
    {
        public Point3d Point { get; set; }
        public int LoadCase { get; set; }
        public Vector3d Force { get; set; }
        public Vector3d Moment { get; set; }

        public StbLoadModel Duplicate()
        {
            return new StbLoadModel
            {
                Point = Point,
                LoadCase = LoadCase,
                Force = Force,
                Moment = Moment,
            };
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

        public override string ToString()
        {
            return "Load LC" + LoadCase + " @ " + Point;
        }
    }
}
