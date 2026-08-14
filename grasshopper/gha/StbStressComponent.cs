using System;
using System.Collections.Generic;
using System.Drawing;
using System.Globalization;
using Grasshopper.Kernel;
using Rhino.Geometry;

namespace StbGrasshopper
{
    public sealed class StbStressComponent : GH_Component
    {
        private readonly List<StressSegment> _segments = new List<StressSegment>();
        private BoundingBox _clippingBox = BoundingBox.Empty;
        private double _legendMaximum;
        private bool _showLegend = true;

        public StbStressComponent()
            : base(
                "STB Stress",
                "STB Stress",
                "Preview maximum absolute normal stress from axial force and biaxial bending.",
                "STB",
                "Results")
        {
        }

        public override Guid ComponentGuid =>
            new Guid("2e602955-531a-4bc3-b6a4-a9b7a2e517ad");

        protected override Bitmap Icon => StbIcons.Forces;

        public override BoundingBox ClippingBox => _clippingBox;

        protected override void RegisterInputParams(GH_InputParamManager pManager)
        {
            pManager.AddGenericParameter(
                "Results",
                "R",
                "Parsed STB result object from STB Analyze.",
                GH_ParamAccess.item);
            pManager.AddIntegerParameter(
                "Load Case",
                "LC",
                "Load case to display.",
                GH_ParamAccess.item,
                0);
            pManager.AddIntegerParameter(
                "Divisions",
                "D",
                "Colored segments per element.",
                GH_ParamAccess.item,
                12);
            pManager.AddNumberParameter(
                "Maximum",
                "Max",
                "Legend maximum stress in N/mm2. Use 0 for automatic.",
                GH_ParamAccess.item,
                0.0);
            pManager.AddBooleanParameter(
                "Legend",
                "Legend",
                "Draw the stress legend in the Rhino viewport.",
                GH_ParamAccess.item,
                true);
        }

        protected override void RegisterOutputParams(GH_OutputParamManager pManager)
        {
            pManager.AddLineParameter(
                "Segments",
                "L",
                "Colored member segments.",
                GH_ParamAccess.list);
            pManager.AddNumberParameter(
                "Stress",
                "S",
                "Maximum absolute normal stress at each segment in N/mm2.",
                GH_ParamAccess.list);
            pManager.AddColourParameter(
                "Colors",
                "C",
                "Preview color for each segment.",
                GH_ParamAccess.list);
        }

        protected override void SolveInstance(IGH_DataAccess da)
        {
            _segments.Clear();
            _clippingBox = BoundingBox.Empty;
            _legendMaximum = 0.0;

            StbParsedResults results = null;
            int loadCase = 0;
            int divisions = 12;
            double requestedMaximum = 0.0;

            if (!da.GetData(0, ref results) || results == null)
            {
                return;
            }

            da.GetData(1, ref loadCase);
            da.GetData(2, ref divisions);
            da.GetData(3, ref requestedMaximum);
            da.GetData(4, ref _showLegend);
            divisions = Math.Max(1, Math.Min(100, divisions));

            if (results.Sections.Count == 0)
            {
                AddRuntimeMessage(
                    GH_RuntimeMessageLevel.Error,
                    "Results contain no SPRP section properties. Re-run STB Analyze.");
                return;
            }

            var nodes = new Dictionary<int, Point3d>();
            foreach (var node in results.Nodes)
            {
                nodes[node.NodeId] = node.Point;
            }

            var elements = new Dictionary<int, StbElementGeometry>();
            foreach (var element in results.Elements)
            {
                elements[element.ElementId] = element;
            }

            var sections = new Dictionary<int, StbSectionProperties>();
            foreach (var section in results.Sections)
            {
                sections[section.SectionId] = section;
            }

            var rawSegments = new List<RawStressSegment>();
            foreach (var force in results.ElementForces)
            {
                if (force.LoadCase != loadCase)
                {
                    continue;
                }

                if (!elements.TryGetValue(force.ElementId, out var element)
                    || !nodes.TryGetValue(element.NodeI, out var start)
                    || !nodes.TryGetValue(element.NodeJ, out var end)
                    || !sections.TryGetValue(element.SectionId, out var section))
                {
                    continue;
                }

                if (section.Area <= 0.0 || section.Wy <= 0.0 || section.Wz <= 0.0)
                {
                    continue;
                }

                var stressI = StressMagnitude(
                    force.Ni,
                    force.Myi,
                    force.Mzi,
                    section);
                var stressJ = StressMagnitude(
                    force.Nj,
                    force.Myj,
                    force.Mzj,
                    section);
                var stressCenter = StressMagnitude(
                    0.5 * (Math.Abs(force.Ni) + Math.Abs(force.Nj)),
                    force.Myc,
                    force.Mzc,
                    section);

                for (var i = 0; i < divisions; i++)
                {
                    var t0 = (double)i / divisions;
                    var t1 = (double)(i + 1) / divisions;
                    var tm = 0.5 * (t0 + t1);
                    var stress = Math.Max(
                        0.0,
                        Quadratic(stressI, stressCenter, stressJ, tm));
                    var line = new Line(
                        Interpolate(start, end, t0),
                        Interpolate(start, end, t1));

                    rawSegments.Add(new RawStressSegment(line, stress));
                    _legendMaximum = Math.Max(_legendMaximum, stress);
                    _clippingBox.Union(line.BoundingBox);
                }
            }

            if (rawSegments.Count == 0)
            {
                AddRuntimeMessage(
                    GH_RuntimeMessageLevel.Warning,
                    "No stress data could be created for load case " + loadCase + ".");
                return;
            }

            if (requestedMaximum > 0.0)
            {
                _legendMaximum = requestedMaximum;
            }

            if (_legendMaximum <= 0.0)
            {
                _legendMaximum = 1.0;
            }

            var outputLines = new List<Line>();
            var outputStress = new List<double>();
            var outputColors = new List<Color>();

            foreach (var segment in rawSegments)
            {
                var color = StressColor(segment.Stress / _legendMaximum);
                _segments.Add(new StressSegment(segment.Line, segment.Stress, color));
                outputLines.Add(segment.Line);
                outputStress.Add(segment.Stress);
                outputColors.Add(color);
            }

            da.SetDataList(0, outputLines);
            da.SetDataList(1, outputStress);
            da.SetDataList(2, outputColors);
        }

        public override void DrawViewportWires(IGH_PreviewArgs args)
        {
            foreach (var segment in _segments)
            {
                args.Display.DrawLine(segment.Line, segment.Color, 5);
            }

            if (_showLegend && _segments.Count > 0)
            {
                DrawLegend(args);
            }
        }

        private void DrawLegend(IGH_PreviewArgs args)
        {
            const int width = 190;
            const int height = 196;
            const int barXOffset = 14;
            const int barYOffset = 38;
            const int barWidth = 24;
            const int barHeight = 132;
            const int steps = 22;

            var viewport = args.Viewport.Bounds;
            var left = Math.Max(viewport.Left + 8, viewport.Right - width - 18);
            var top = viewport.Top + 18;
            var panel = new Rectangle(left, top, width, height);

            args.Display.Draw2dRectangle(
                panel,
                Color.FromArgb(220, 30, 34, 38),
                1,
                Color.FromArgb(230, 220, 225, 230));
            args.Display.Draw2dText(
                "Max normal stress [N/mm2]",
                Color.White,
                new Point2d(left + 10, top + 11),
                false,
                12);

            for (var i = 0; i < steps; i++)
            {
                var normalized = 1.0 - (double)i / (steps - 1);
                var y0 = top + barYOffset + i * barHeight / steps;
                var y1 = top + barYOffset + (i + 1) * barHeight / steps;
                args.Display.Draw2dRectangle(
                    new Rectangle(
                        left + barXOffset,
                        y0,
                        barWidth,
                        Math.Max(1, y1 - y0 + 1)),
                    StressColor(normalized),
                    0,
                    StressColor(normalized));
            }

            DrawLegendValue(args, left + 48, top + barYOffset - 5, _legendMaximum);
            DrawLegendValue(
                args,
                left + 48,
                top + barYOffset + barHeight / 2 - 5,
                _legendMaximum * 0.5);
            DrawLegendValue(args, left + 48, top + barYOffset + barHeight - 5, 0.0);
        }

        private static void DrawLegendValue(
            IGH_PreviewArgs args,
            int x,
            int y,
            double value)
        {
            args.Display.Draw2dText(
                value.ToString("0.###", CultureInfo.InvariantCulture),
                Color.White,
                new Point2d(x, y),
                false,
                12);
        }

        private static double StressMagnitude(
            double axialForce,
            double momentY,
            double momentZ,
            StbSectionProperties section)
        {
            var axial = Math.Abs(axialForce) * 1e3 / section.Area;
            var bendingY = Math.Abs(momentY) * 1e6 / section.Wy;
            var bendingZ = Math.Abs(momentZ) * 1e6 / section.Wz;
            return axial + bendingY + bendingZ;
        }

        private static double Quadratic(double value0, double center, double value1, double t)
        {
            var l0 = 2.0 * (t - 0.5) * (t - 1.0);
            var lc = 4.0 * t * (1.0 - t);
            var l1 = 2.0 * t * (t - 0.5);
            return value0 * l0 + center * lc + value1 * l1;
        }

        private static Point3d Interpolate(Point3d start, Point3d end, double t)
        {
            return start + (end - start) * t;
        }

        private static Color StressColor(double normalized)
        {
            var t = Math.Max(0.0, Math.Min(1.0, normalized));
            if (t <= 0.25)
            {
                return Blend(Color.FromArgb(38, 70, 190), Color.FromArgb(0, 190, 240), t / 0.25);
            }

            if (t <= 0.5)
            {
                return Blend(Color.FromArgb(0, 190, 240), Color.FromArgb(20, 195, 105), (t - 0.25) / 0.25);
            }

            if (t <= 0.75)
            {
                return Blend(Color.FromArgb(20, 195, 105), Color.FromArgb(255, 220, 45), (t - 0.5) / 0.25);
            }

            return Blend(Color.FromArgb(255, 220, 45), Color.FromArgb(225, 45, 35), (t - 0.75) / 0.25);
        }

        private static Color Blend(Color start, Color end, double t)
        {
            return Color.FromArgb(
                (int)Math.Round(start.R + (end.R - start.R) * t),
                (int)Math.Round(start.G + (end.G - start.G) * t),
                (int)Math.Round(start.B + (end.B - start.B) * t));
        }

        private sealed class RawStressSegment
        {
            public RawStressSegment(Line line, double stress)
            {
                Line = line;
                Stress = stress;
            }

            public Line Line { get; }
            public double Stress { get; }
        }

        private sealed class StressSegment
        {
            public StressSegment(Line line, double stress, Color color)
            {
                Line = line;
                Stress = stress;
                Color = color;
            }

            public Line Line { get; }
            public double Stress { get; }
            public Color Color { get; }
        }
    }
}
