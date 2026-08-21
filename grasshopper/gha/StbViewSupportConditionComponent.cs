using System;
using System.Collections.Generic;
using System.Drawing;
using System.Globalization;
using Grasshopper.Kernel;
using Rhino.Display;
using Rhino.Geometry;

namespace StbGrasshopper
{
    public sealed class StbViewSupportConditionComponent : GH_Component
    {
        private readonly List<SupportGlyph> _glyphs = new List<SupportGlyph>();
        private BoundingBox _clippingBox = BoundingBox.Empty;
        private double _size = 0.35;

        public StbViewSupportConditionComponent()
            : base(
                "View Support Condition",
                "View Sup",
                "Display STB support conditions as consistent 3D symbols.",
                "STB",
                "View")
        {
        }

        public override Guid ComponentGuid => new Guid("f7a8b9c0-1234-4456-0789-abcdef012345");
        protected override Bitmap Icon => StbIcons.Support;
        public override BoundingBox ClippingBox => _clippingBox;

        protected override void RegisterInputParams(GH_InputParamManager pManager)
        {
            pManager.AddParameter(new StbModelParameter(), "STb Model", "STb Model", "Assembled STb Model.", GH_ParamAccess.item);
            pManager.AddNumberParameter("Size", "S", "Support symbol size in model units.", GH_ParamAccess.item, 0.35);
        }

        protected override void RegisterOutputParams(GH_OutputParamManager pManager)
        {
            pManager.AddPointParameter("Points", "P", "Support locations.", GH_ParamAccess.list);
            pManager.AddBrepParameter("Symbols", "B", "Support symbol Breps.", GH_ParamAccess.list);
            pManager.AddTextParameter("Conditions", "C", "Support condition descriptions.", GH_ParamAccess.list);
        }

        protected override void SolveInstance(IGH_DataAccess da)
        {
            StbModelModel model;
            if (!StbModelGooUtil.TryGetModel(da, 0, out model))
            {
                return;
            }

            var size = _size;
            da.GetData(1, ref size);
            _size = Math.Max(0.01, size);
            _glyphs.Clear();
            _clippingBox = BoundingBox.Empty;

            var points = new List<Point3d>();
            var symbols = new List<Brep>();
            var conditions = new List<string>();
            foreach (var support in model.Supports)
            {
                if (support == null || !support.Point.IsValid)
                {
                    continue;
                }

                var glyph = BuildGlyph(support, _size);
                _glyphs.Add(glyph);
                points.Add(support.Point);
                symbols.AddRange(glyph.Breps);
                conditions.Add(glyph.Description);
                foreach (var brep in glyph.Breps)
                {
                    _clippingBox.Union(brep.GetBoundingBox(true));
                }
            }

            da.SetDataList(0, points);
            da.SetDataList(1, symbols);
            da.SetDataList(2, conditions);
        }

        public override void DrawViewportMeshes(IGH_PreviewArgs args)
        {
            foreach (var glyph in _glyphs)
            {
                for (var i = 0; i < glyph.Breps.Count; i++)
                {
                    args.Display.DrawBrepShaded(glyph.Breps[i], new DisplayMaterial(glyph.Colors[i]));
                }
            }
        }

        public override void DrawViewportWires(IGH_PreviewArgs args)
        {
            foreach (var glyph in _glyphs)
            {
                foreach (var brep in glyph.Breps)
                {
                    args.Display.DrawBrepWires(brep, Color.FromArgb(45, 50, 55), 1);
                }

                foreach (var rail in glyph.Rails)
                {
                    args.Display.DrawLine(rail, Color.FromArgb(55, 65, 70), 2);
                }
            }
        }

        private static SupportGlyph BuildGlyph(StbSupportModel support, double size)
        {
            var glyph = new SupportGlyph();
            var allTranslations = support.Tx && support.Ty && support.Tz;
            var noTranslations = !support.Tx && !support.Ty && !support.Tz;
            var allRotations = support.Rx && support.Ry && support.Rz;
            var noRotations = !support.Rx && !support.Ry && !support.Rz;
            var darkGreen = Color.FromArgb(35, 105, 65);
            var transparentGreen = Color.FromArgb(90, 80, 170, 110);
            var blue = Color.FromArgb(40, 105, 175);
            var orange = Color.FromArgb(220, 145, 30);
            var red = Color.FromArgb(190, 55, 105);

            if (allTranslations && allRotations)
            {
                glyph.Add(BoxAt(support.Point, size), darkGreen);
            }
            else if (noTranslations)
            {
                glyph.Add(BoxAt(support.Point, size * 0.72), transparentGreen);
                AddRotationCylinders(glyph, support, size, red, onlyFixed: true);
            }
            else if (allTranslations)
            {
                if (noRotations)
                {
                    glyph.Add(SquarePyramidAt(support.Point, size), blue);
                    glyph.Add(AxisCylinder(support.Point, Vector3d.ZAxis, size), red);
                }
                else if (!support.Rx && !support.Ry && support.Rz)
                {
                    glyph.Add(SquarePyramidAt(support.Point, size), blue);
                }
                else if (!support.Rx && support.Ry && support.Rz)
                {
                    glyph.Add(TrianglePrismAlongX(support.Point, size), blue);
                    glyph.Add(AxisCylinder(support.Point, Vector3d.XAxis, size), red);
                }
                else if (support.Rx && !support.Ry && support.Rz)
                {
                    glyph.Add(TrianglePrismAlongY(support.Point, size), blue);
                    glyph.Add(AxisCylinder(support.Point, Vector3d.YAxis, size), red);
                }
                else
                {
                    glyph.Add(SquarePyramidAt(support.Point, size), blue);
                    AddRotationCylinders(glyph, support, size, red, onlyFixed: true);
                }
            }
            else
            {
                glyph.Add(BoxAt(support.Point, size * 0.72), transparentGreen);
                AddTranslationMarkers(glyph, support, size, orange);
                AddRotationCylinders(glyph, support, size, red, onlyFixed: true);
            }

            if (support.Tx && support.Ty && !support.Tz)
            {
                AddZRails(glyph, support.Point, size);
            }

            glyph.Description = ConditionText(support, allTranslations, allRotations, noTranslations);
            return glyph;
        }

        private static void AddTranslationMarkers(SupportGlyph glyph, StbSupportModel support, double size, Color color)
        {
            if (!support.Tx) glyph.Add(BoxAt(support.Point + Vector3d.XAxis * size * 0.62, size * 0.12, size * 0.9, size * 0.9), color);
            if (!support.Ty) glyph.Add(BoxAt(support.Point + Vector3d.YAxis * size * 0.62, size * 0.12, size * 0.9, size * 0.9), color);
            if (!support.Tz) glyph.Add(BoxAt(support.Point - Vector3d.ZAxis * size * 0.72, size * 0.12, size * 1.25, size * 1.25), color);
        }

        private static void AddRotationCylinders(SupportGlyph glyph, StbSupportModel support, double size, Color color, bool onlyFixed = false)
        {
            if (support.Rx == onlyFixed) glyph.Add(AxisCylinder(support.Point, Vector3d.XAxis, size), color);
            if (support.Ry == onlyFixed) glyph.Add(AxisCylinder(support.Point, Vector3d.YAxis, size), color);
            if (support.Rz == onlyFixed) glyph.Add(AxisCylinder(support.Point, Vector3d.ZAxis, size), color);
        }

        private static void AddZRails(SupportGlyph glyph, Point3d point, double size)
        {
            var half = size * 0.48;
            var bottom = point - Vector3d.ZAxis * size * 0.72;
            glyph.Rails.Add(new Line(bottom + Vector3d.XAxis * half, bottom + Vector3d.XAxis * half + Vector3d.ZAxis * size * 0.62));
            glyph.Rails.Add(new Line(bottom - Vector3d.XAxis * half, bottom - Vector3d.XAxis * half + Vector3d.ZAxis * size * 0.62));
        }

        private static string ConditionText(StbSupportModel support, bool allTranslations, bool allRotations, bool noTranslations)
        {
            var translation = (support.Tx ? "Tx " : "") + (support.Ty ? "Ty " : "") + (support.Tz ? "Tz" : "");
            var rotation = (support.Rx ? "Rx " : "") + (support.Ry ? "Ry " : "") + (support.Rz ? "Rz" : "");
            var type = allTranslations && allRotations
                ? "Fixed"
                : noTranslations
                    ? "Free translation"
                    : allTranslations
                        ? "Pinned / rotational"
                        : "Partial translation";
            return type + " [" + translation.Trim() + (rotation.Length > 0 ? "; " + rotation.Trim() : "") + "]";
        }

        private static Brep BoxAt(Point3d point, double size)
        {
            return BoxAt(point, size, size, size);
        }

        private static Brep BoxAt(Point3d point, double height, double width, double depth)
        {
            var box = new Box(
                new Plane(point - Vector3d.ZAxis * height, Vector3d.ZAxis),
                new Interval(-width * 0.5, width * 0.5),
                new Interval(-depth * 0.5, depth * 0.5),
                new Interval(0.0, height));
            return box.ToBrep();
        }

        private static Brep SquarePyramidAt(Point3d point, double size)
        {
            var bottom = point - Vector3d.ZAxis * size;
            var half = size * 0.75;
            var mesh = new Mesh();
            var a = mesh.Vertices.Add(bottom + new Vector3d(-half, -half, 0));
            var b = mesh.Vertices.Add(bottom + new Vector3d(half, -half, 0));
            var c = mesh.Vertices.Add(bottom + new Vector3d(half, half, 0));
            var d = mesh.Vertices.Add(bottom + new Vector3d(-half, half, 0));
            var apex = mesh.Vertices.Add(point);
            mesh.Faces.AddFace(a, b, apex);
            mesh.Faces.AddFace(b, c, apex);
            mesh.Faces.AddFace(c, d, apex);
            mesh.Faces.AddFace(d, a, apex);
            mesh.Faces.AddFace(d, c, b, a);
            mesh.Normals.ComputeNormals();
            return Brep.CreateFromMesh(mesh, true);
        }

        private static Brep TrianglePrismAlongX(Point3d point, double size)
        {
            var halfLength = size * 0.52;
            var halfWidth = size * 0.5;
            var height = size * Math.Sqrt(3.0) * 0.5;
            var vertices = new[]
            {
                point - Vector3d.XAxis * halfLength + Vector3d.YAxis * halfWidth - Vector3d.ZAxis * height,
                point - Vector3d.XAxis * halfLength - Vector3d.YAxis * halfWidth - Vector3d.ZAxis * height,
                point - Vector3d.XAxis * halfLength,
                point + Vector3d.XAxis * halfLength + Vector3d.YAxis * halfWidth - Vector3d.ZAxis * height,
                point + Vector3d.XAxis * halfLength - Vector3d.YAxis * halfWidth - Vector3d.ZAxis * height,
                point + Vector3d.XAxis * halfLength,
            };
            return TrianglePrism(vertices);
        }

        private static Brep TrianglePrismAlongY(Point3d point, double size)
        {
            var halfLength = size * 0.52;
            var halfWidth = size * 0.5;
            var height = size * Math.Sqrt(3.0) * 0.5;
            var vertices = new[]
            {
                point - Vector3d.YAxis * halfLength + Vector3d.XAxis * halfWidth - Vector3d.ZAxis * height,
                point - Vector3d.YAxis * halfLength - Vector3d.XAxis * halfWidth - Vector3d.ZAxis * height,
                point - Vector3d.YAxis * halfLength,
                point + Vector3d.YAxis * halfLength + Vector3d.XAxis * halfWidth - Vector3d.ZAxis * height,
                point + Vector3d.YAxis * halfLength - Vector3d.XAxis * halfWidth - Vector3d.ZAxis * height,
                point + Vector3d.YAxis * halfLength,
            };
            return TrianglePrism(vertices);
        }

        private static Brep TrianglePrism(IReadOnlyList<Point3d> vertices)
        {
            var mesh = new Mesh();
            for (var i = 0; i < vertices.Count; i++) mesh.Vertices.Add(vertices[i]);
            mesh.Faces.AddFace(0, 1, 2);
            mesh.Faces.AddFace(3, 5, 4);
            mesh.Faces.AddFace(0, 3, 4, 1);
            mesh.Faces.AddFace(1, 4, 5, 2);
            mesh.Faces.AddFace(2, 5, 3, 0);
            mesh.Normals.ComputeNormals();
            return Brep.CreateFromMesh(mesh, true);
        }

        private static Brep AxisCylinder(Point3d point, Vector3d axis, double size)
        {
            var plane = new Plane(point - axis * size * 0.45, axis);
            var cylinder = new Cylinder(new Circle(plane, size * 0.16), size * 0.9);
            return cylinder.ToBrep(true, true);
        }

        private sealed class SupportGlyph
        {
            public List<Brep> Breps { get; } = new List<Brep>();
            public List<Color> Colors { get; } = new List<Color>();
            public List<Line> Rails { get; } = new List<Line>();
            public string Description { get; set; } = string.Empty;

            public void Add(Brep brep, Color color)
            {
                if (brep != null)
                {
                    Breps.Add(brep);
                    Colors.Add(color);
                }
            }
        }
    }
}
