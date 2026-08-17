using System;
using System.Collections.Generic;
using System.Drawing;
using System.Globalization;
using System.Windows.Forms;
using Grasshopper.GUI;
using Grasshopper.GUI.Canvas;
using Grasshopper.Kernel;
using Grasshopper.Kernel.Attributes;
using GH_IO.Serialization;
using Rhino.Geometry;

namespace StbGrasshopper
{
    public sealed class StbForceDiagramComponent : GH_Component
    {
        private readonly List<DiagramSegment> _segments = new List<DiagramSegment>();
        private readonly List<Line> _constructionLines = new List<Line>();
        private BoundingBox _clippingBox = BoundingBox.Empty;
        private double _legendMaximum;
        private string _componentLabel = "Nx";
        private string _unitLabel = "kN";
        private bool _showValues = true;
        private bool _showLegend = true;
        private double _diagramScale = 0.1;
        private double _diagramScaleMinimum = 0.0;
        private double _diagramScaleMaximum = 1.0;
        private double _textSize = 2.0;
        private double _textSizeMinimum = 0.5;
        private double _textSizeMaximum = 10.0;

        public StbForceDiagramComponent()
            : base(
                "STB Force Diagram",
                "STB FDiagram",
                "Draw a selected member force diagram and output its values in kN or kNm.",
                "STB",
                "Results")
        {
        }

        public override Guid ComponentGuid =>
            new Guid("7a7f6f8c-62a2-4e07-9ef3-0b1c8d6e4f51");

        protected override Bitmap Icon => StbIcons.Forces;

        public override BoundingBox ClippingBox => _clippingBox;

        public override void CreateAttributes()
        {
            m_attributes = new StbForceDiagramAttributes(this);
        }

        protected override void RegisterInputParams(GH_InputParamManager pManager)
        {
            pManager.AddGenericParameter("Results", "R", "Parsed STB result object from STB Analyze.", GH_ParamAccess.item);
            pManager.AddIntegerParameter("Load Case", "LC", "Load case to display. Negative means all load cases.", GH_ParamAccess.item, 0);
            pManager.AddIntegerParameter("Component", "C", "1=Nx, 2=Vy, 3=Vz, 4=Mx, 5=My, 6=Mz.", GH_ParamAccess.item, 1);
            pManager.AddIntegerParameter("Divisions", "D", "Diagram segments per element.", GH_ParamAccess.item, 8);
            pManager.AddNumberParameter("Maximum", "Max", "Legend maximum in kN or kNm. Use 0 for automatic.", GH_ParamAccess.item, 0.0);
            pManager.AddBooleanParameter("Values", "V", "Show value labels in the Rhino viewport.", GH_ParamAccess.item, true);
            pManager.AddBooleanParameter("Legend", "Legend", "Draw the force legend in the Rhino viewport.", GH_ParamAccess.item, true);
        }

        protected override void RegisterOutputParams(GH_OutputParamManager pManager)
        {
            pManager.AddLineParameter("Diagram", "D", "Force diagram segments.", GH_ParamAccess.list);
            pManager.AddNumberParameter("Values", "V", "Signed force value at the midpoint of each diagram segment in kN or kNm.", GH_ParamAccess.list);
            pManager.AddIntegerParameter("Element IDs", "E", "Element id for each diagram segment.", GH_ParamAccess.list);
            pManager.AddTextParameter("Component", "C", "Displayed force component and unit.", GH_ParamAccess.item);
        }

        protected override void SolveInstance(IGH_DataAccess da)
        {
            _segments.Clear();
            _constructionLines.Clear();
            _clippingBox = BoundingBox.Empty;
            _legendMaximum = 0.0;

            StbParsedResults results = null;
            int loadCase = 0;
            int component = 1;
            int divisions = 8;
            double requestedMaximum = 0.0;

            if (!da.GetData(0, ref results) || results == null)
            {
                return;
            }

            da.GetData(1, ref loadCase);
            da.GetData(2, ref component);
            da.GetData(3, ref divisions);
            var showValues = true;
            var showLegend = true;
            ReadInput(da, "Maximum", ref requestedMaximum);
            ReadInput(da, "Values", ref showValues);
            ReadInput(da, "Legend", ref showLegend);
            _showValues = showValues;
            _showLegend = showLegend;

            if (!TryGetComponent(component, out var componentInfo))
            {
                AddRuntimeMessage(GH_RuntimeMessageLevel.Error, "Component must be 1=Nx, 2=Vy, 3=Vz, 4=Mx, 5=My, or 6=Mz.");
                return;
            }

            divisions = Math.Max(1, Math.Min(100, divisions));
            _componentLabel = componentInfo.Label;
            _unitLabel = componentInfo.Unit;

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

            var rawSegments = new List<RawDiagramSegment>();
            foreach (var force in results.ElementForces)
            {
                if (!StbLoadCaseFilter.Matches(loadCase, force.LoadCase)
                    || !elements.TryGetValue(force.ElementId, out var element)
                    || !nodes.TryGetValue(element.NodeI, out var start)
                    || !nodes.TryGetValue(element.NodeJ, out var end))
                {
                    continue;
                }

                var axis = end - start;
                if (axis.Length <= 1e-9)
                {
                    continue;
                }

                axis.Unitize();
                var localY = LocalYAxis(axis);
                var localZ = Vector3d.CrossProduct(axis, localY);
                localZ.Unitize();
                var diagramDirection = DiagramDirection(componentInfo.Label, localY, localZ);
                var textNormal = Vector3d.CrossProduct(axis, diagramDirection);
                textNormal.Unitize();
                GetForceValues(force, componentInfo, out var valueI, out var valueCenter, out var valueJ);
                _legendMaximum = Math.Max(_legendMaximum, Math.Max(Math.Abs(valueI), Math.Max(Math.Abs(valueCenter), Math.Abs(valueJ))));

                var points = new List<Point3d>();
                for (var i = 0; i <= divisions; i++)
                {
                    var t = (double)i / divisions;
                    var basePoint = start + (end - start) * t;
                    var value = InterpolateForce(valueI, valueCenter, valueJ, t);
                    points.Add(basePoint + diagramDirection * (value * _diagramScale));
                }

                for (var i = 0; i < divisions; i++)
                {
                    var t0 = (double)i / divisions;
                    var t1 = (double)(i + 1) / divisions;
                    var value = InterpolateForce(valueI, valueCenter, valueJ, 0.5 * (t0 + t1));
                    var line = new Line(points[i], points[i + 1]);
                    rawSegments.Add(new RawDiagramSegment(line, value, force.ElementId, textNormal));
                    ExtendClippingBox(line.BoundingBox);

                    var baseline = new Line(
                        start + (end - start) * t0,
                        start + (end - start) * t1);
                    _constructionLines.Add(baseline);
                    _constructionLines.Add(new Line(baseline.From, line.From));
                    if (i == divisions - 1)
                    {
                        _constructionLines.Add(new Line(baseline.To, line.To));
                    }
                    ExtendClippingBox(baseline.BoundingBox);
                }
            }

            if (rawSegments.Count == 0)
            {
                AddRuntimeMessage(GH_RuntimeMessageLevel.Warning, "No force data could be created for load case " + loadCase + ".");
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
            var outputValues = new List<double>();
            var outputElementIds = new List<int>();
            foreach (var segment in rawSegments)
            {
                var color = ForceColor(Math.Abs(segment.Value) / _legendMaximum);
                _segments.Add(new DiagramSegment(segment.Line, segment.Value, segment.ElementId, segment.TextNormal, color));
                outputLines.Add(segment.Line);
                outputValues.Add(segment.Value);
                outputElementIds.Add(segment.ElementId);
            }

            da.SetDataList(0, outputLines);
            da.SetDataList(1, outputValues);
            da.SetDataList(2, outputElementIds);
            da.SetData(3, _componentLabel + " [" + _unitLabel + "]");
        }

        internal double DiagramScale => _diagramScale;

        internal double DiagramScaleMinimum => _diagramScaleMinimum;

        internal double DiagramScaleMaximum => _diagramScaleMaximum;

        internal double TextSize => _textSize;

        internal double TextSizeMinimum => _textSizeMinimum;

        internal double TextSizeMaximum => _textSizeMaximum;

        internal void SetDiagramScale(double value)
        {
            _diagramScale = Math.Max(_diagramScaleMinimum, Math.Min(_diagramScaleMaximum, value));
            ExpireSolution(true);
        }

        internal void SetTextSize(double value)
        {
            _textSize = Math.Max(_textSizeMinimum, Math.Min(_textSizeMaximum, value));
            ExpireSolution(true);
        }

        internal void EditDiagramScaleRange()
        {
            var minimum = _diagramScaleMinimum;
            if (!Rhino.UI.Dialogs.ShowNumberBox(
                "Diagram scale range",
                "Minimum value",
                ref minimum,
                0.0,
                _diagramScaleMaximum - 0.01))
            {
                return;
            }

            var maximum = _diagramScaleMaximum;
            if (Rhino.UI.Dialogs.ShowNumberBox(
                "Diagram scale range",
                "Maximum value",
                ref maximum,
                minimum + 0.01,
                100.0))
            {
                _diagramScaleMinimum = minimum;
                _diagramScaleMaximum = maximum;
                _diagramScale = Math.Max(minimum, Math.Min(_diagramScale, maximum));
                ExpireSolution(true);
            }
        }

        internal void EditTextSizeRange()
        {
            var minimum = _textSizeMinimum;
            if (!Rhino.UI.Dialogs.ShowNumberBox(
                "Text size range",
                "Minimum value",
                ref minimum,
                0.1,
                _textSizeMaximum - 0.1))
            {
                return;
            }

            var maximum = _textSizeMaximum;
            if (Rhino.UI.Dialogs.ShowNumberBox(
                "Text size range",
                "Maximum value",
                ref maximum,
                minimum + 0.1,
                100.0))
            {
                _textSizeMinimum = minimum;
                _textSizeMaximum = maximum;
                _textSize = Math.Max(minimum, Math.Min(_textSize, maximum));
                ExpireSolution(true);
            }
        }

        public override bool Write(GH_IWriter writer)
        {
            writer.SetDouble("DiagramScale", _diagramScale);
            writer.SetDouble("DiagramScaleMinimum", _diagramScaleMinimum);
            writer.SetDouble("DiagramScaleMaximum", _diagramScaleMaximum);
            writer.SetDouble("TextSize", _textSize);
            writer.SetDouble("TextSizeMinimum", _textSizeMinimum);
            writer.SetDouble("TextSizeMaximum", _textSizeMaximum);
            return base.Write(writer);
        }

        public override bool Read(GH_IReader reader)
        {
            if (reader.ItemExists("DiagramScale"))
            {
                _diagramScale = reader.GetDouble("DiagramScale");
            }

            if (reader.ItemExists("TextSize"))
            {
                _textSize = reader.GetDouble("TextSize");
            }

            if (reader.ItemExists("DiagramScaleMaximum"))
            {
                _diagramScaleMaximum = reader.GetDouble("DiagramScaleMaximum");
            }

            if (reader.ItemExists("DiagramScaleMinimum"))
            {
                _diagramScaleMinimum = reader.GetDouble("DiagramScaleMinimum");
            }

            if (reader.ItemExists("TextSizeMaximum"))
            {
                _textSizeMaximum = reader.GetDouble("TextSizeMaximum");
            }

            if (reader.ItemExists("TextSizeMinimum"))
            {
                _textSizeMinimum = reader.GetDouble("TextSizeMinimum");
            }

            return base.Read(reader);
        }

        public override void DrawViewportWires(IGH_PreviewArgs args)
        {
            foreach (var line in _constructionLines)
            {
                args.Display.DrawLine(line, Color.FromArgb(100, 150, 150, 150), 1);
            }

            foreach (var segment in _segments)
            {
                args.Display.DrawLine(segment.Line, segment.Color, 4);
                if (_showValues)
                {
                    var midpoint = segment.Line.PointAt(0.5);
                    args.Display.Draw3dText(
                        segment.Value.ToString("0.###", CultureInfo.InvariantCulture),
                        Color.White,
                        new Plane(midpoint, args.Viewport.CameraX, args.Viewport.CameraY),
                        _textSize,
                        "Arial",
                        false,
                        false,
                        Rhino.DocObjects.TextHorizontalAlignment.Center,
                        Rhino.DocObjects.TextVerticalAlignment.Middle);
                }
            }

            if (_showLegend && _segments.Count > 0)
            {
                DrawLegend(args);
            }
        }

        private void ExtendClippingBox(BoundingBox box)
        {
            if (!_clippingBox.IsValid)
            {
                _clippingBox = box;
                return;
            }

            _clippingBox.Union(box);
        }

        private bool ReadInput<T>(IGH_DataAccess dataAccess, string name, ref T value)
        {
            for (var index = 0; index < Params.Input.Count; index++)
            {
                if (string.Equals(Params.Input[index].Name, name, StringComparison.Ordinal))
                {
                    return dataAccess.GetData(index, ref value);
                }
            }

            return false;
        }

        private static Vector3d LocalYAxis(Vector3d axis)
        {
            var localY = Vector3d.CrossProduct(Vector3d.ZAxis, axis);
            if (localY.Length <= 1e-9)
            {
                localY = Vector3d.XAxis;
            }

            localY.Unitize();
            return localY;
        }

        private static Vector3d DiagramDirection(string label, Vector3d localY, Vector3d localZ)
        {
            switch (label)
            {
                case "Vy":
                case "Mz":
                    return localY;
                case "Vz":
                case "My":
                    if (label == "My")
                    {
                        return -localZ;
                    }

                    return localZ;
                case "Nx":
                case "Mx":
                default:
                    return localZ;
            }
        }

        private void DrawLegend(IGH_PreviewArgs args)
        {
            const int width = 190;
            const int height = 160;
            const int barXOffset = 14;
            const int barYOffset = 38;
            const int barWidth = 24;
            const int barHeight = 96;
            const int steps = 18;

            var viewport = args.Viewport.Bounds;
            var left = Math.Max(viewport.Left + 8, viewport.Right - width - 18);
            var top = viewport.Top + 18;
            var panel = new Rectangle(left, top, width, height);
            args.Display.Draw2dRectangle(panel, Color.FromArgb(220, 30, 34, 38), 1, Color.FromArgb(230, 220, 225, 230));
            args.Display.Draw2dText(_componentLabel + " [" + _unitLabel + "]", Color.White, new Point2d(left + 10, top + 11), false, 12);

            for (var i = 0; i < steps; i++)
            {
                var normalized = 1.0 - (double)i / (steps - 1);
                var y0 = top + barYOffset + i * barHeight / steps;
                var y1 = top + barYOffset + (i + 1) * barHeight / steps;
                args.Display.Draw2dRectangle(
                    new Rectangle(left + barXOffset, y0, barWidth, Math.Max(1, y1 - y0 + 1)),
                    ForceColor(normalized), 0, ForceColor(normalized));
            }

            DrawLegendValue(args, left + 48, top + barYOffset - 5, _legendMaximum);
            DrawLegendValue(args, left + 48, top + barYOffset + barHeight / 2 - 5, 0.0);
            DrawLegendValue(args, left + 48, top + barYOffset + barHeight - 5, -_legendMaximum);
        }

        private static void DrawLegendValue(IGH_PreviewArgs args, int x, int y, double value)
        {
            args.Display.Draw2dText(value.ToString("0.###", CultureInfo.InvariantCulture), Color.White, new Point2d(x, y), false, 12);
        }

        private static bool TryGetComponent(int component, out ForceComponentInfo info)
        {
            switch (component)
            {
                case 1: info = new ForceComponentInfo("Nx", "kN", (f, end) => end ? f.Nj : f.Ni); return true;
                case 2: info = new ForceComponentInfo("Vy", "kN", (f, end) => end ? f.Qyj : f.Qyi); return true;
                case 3: info = new ForceComponentInfo("Vz", "kN", (f, end) => end ? f.Qzj : f.Qzi); return true;
                case 4: info = new ForceComponentInfo("Mx", "kNm", (f, end) => end ? f.Mxj : f.Mxi); return true;
                case 5: info = new ForceComponentInfo("My", "kNm", (f, end) => end ? f.Myj : f.Myi); return true;
                case 6: info = new ForceComponentInfo("Mz", "kNm", (f, end) => end ? f.Mzj : f.Mzi); return true;
                default: info = null; return false;
            }
        }

        private static void GetForceValues(ElementForce force, ForceComponentInfo info, out double valueI, out double valueCenter, out double valueJ)
        {
            valueI = info.Value(force, false);
            valueJ = info.Value(force, true);
            valueCenter = valueI + 0.5 * (valueJ - valueI);
            if (info.Label == "My") valueCenter = force.Myc;
            if (info.Label == "Mz") valueCenter = force.Mzc;
        }

        private static double InterpolateForce(double valueI, double valueCenter, double valueJ, double t)
        {
            var l0 = 2.0 * (t - 0.5) * (t - 1.0);
            var lc = 4.0 * t * (1.0 - t);
            var l1 = 2.0 * t * (t - 0.5);
            return valueI * l0 + valueCenter * lc + valueJ * l1;
        }

        private static Color ForceColor(double normalized)
        {
            var t = Math.Max(0.0, Math.Min(1.0, normalized));
            return Blend(Color.FromArgb(35, 100, 210), Color.FromArgb(225, 45, 35), t);
        }

        private static Color Blend(Color start, Color end, double t)
        {
            return Color.FromArgb(
                (int)Math.Round(start.R + (end.R - start.R) * t),
                (int)Math.Round(start.G + (end.G - start.G) * t),
                (int)Math.Round(start.B + (end.B - start.B) * t));
        }

        private sealed class ForceComponentInfo
        {
            public ForceComponentInfo(string label, string unit, Func<ElementForce, bool, double> value)
            {
                Label = label;
                Unit = unit;
                Value = value;
            }

            public string Label { get; }
            public string Unit { get; }
            public Func<ElementForce, bool, double> Value { get; }
        }

        private sealed class RawDiagramSegment
        {
            public RawDiagramSegment(Line line, double value, int elementId, Vector3d textNormal)
            {
                Line = line;
                Value = value;
                ElementId = elementId;
                TextNormal = textNormal;
            }

            public Line Line { get; }
            public double Value { get; }
            public int ElementId { get; }
            public Vector3d TextNormal { get; }
        }

        private sealed class DiagramSegment
        {
            public DiagramSegment(Line line, double value, int elementId, Vector3d textNormal, Color color)
            {
                Line = line;
                Value = value;
                ElementId = elementId;
                TextNormal = textNormal;
                Color = color;
            }

            public Line Line { get; }
            public double Value { get; }
            public int ElementId { get; }
            public Vector3d TextNormal { get; }
            public Color Color { get; }
        }
    }

    internal sealed class StbForceDiagramAttributes : GH_ComponentAttributes
    {
        private static readonly Color TrackColor = Color.FromArgb(70, 76, 82);
        private static readonly Color FillColor = Color.FromArgb(45, 170, 210);
        private readonly StbForceDiagramComponent _owner;
        private RectangleF _scaleBounds;
        private RectangleF _textBounds;
        private int _draggingSlider;

        public StbForceDiagramAttributes(StbForceDiagramComponent owner)
            : base(owner)
        {
            _owner = owner;
        }

        protected override void Layout()
        {
            base.Layout();

            const float stripHeight = 54f;
            const float margin = 4f;
            var original = Bounds;
            const float minimumWidth = 210f;
            var width = Math.Max(original.Width, minimumWidth);
            var left = original.X - (width - original.Width) * 0.5f;
            Bounds = new RectangleF(
                left,
                original.Y,
                width,
                original.Height + stripHeight);

            var inputOffset = Bounds.Left - original.Left;
            foreach (var input in _owner.Params.Input)
            {
                if (input.Attributes == null)
                {
                    continue;
                }

                var parameterBounds = input.Attributes.Bounds;
                parameterBounds.Offset(inputOffset, 0f);
                input.Attributes.Bounds = parameterBounds;
                var pivot = input.Attributes.Pivot;
                input.Attributes.Pivot = new PointF(pivot.X + inputOffset, pivot.Y);
            }

            var outputOffset = Bounds.Right - original.Right;
            foreach (var output in _owner.Params.Output)
            {
                if (output.Attributes == null)
                {
                    continue;
                }

                var parameterBounds = output.Attributes.Bounds;
                parameterBounds.Offset(outputOffset, 0f);
                output.Attributes.Bounds = parameterBounds;
                var pivot = output.Attributes.Pivot;
                output.Attributes.Pivot = new PointF(pivot.X + outputOffset, pivot.Y);
            }

            var rowWidth = Bounds.Width - 2f * margin;
            _scaleBounds = new RectangleF(
                Bounds.Left + margin,
                original.Bottom + 5f,
                rowWidth,
                18f);
            _textBounds = new RectangleF(
                Bounds.Left + margin,
                original.Bottom + 29f,
                rowWidth,
                18f);
        }

        protected override void Render(
            GH_Canvas canvas,
            Graphics graphics,
            GH_CanvasChannel channel)
        {
            base.Render(canvas, graphics, channel);
            if (channel != GH_CanvasChannel.Objects)
            {
                return;
            }

            DrawSlider(graphics, _scaleBounds, "Diagram scale", _owner.DiagramScale, _owner.DiagramScaleMinimum, _owner.DiagramScaleMaximum, "0.###");
            DrawSlider(graphics, _textBounds, "Text size", _owner.TextSize, _owner.TextSizeMinimum, _owner.TextSizeMaximum, "0.##");
        }

        public override GH_ObjectResponse RespondToMouseDown(
            GH_Canvas sender,
            GH_CanvasMouseEvent e)
        {
            if (e.Button == MouseButtons.Left)
            {
                if (_scaleBounds.Contains(e.CanvasLocation))
                {
                    _draggingSlider = 1;
                    UpdateSlider(e.CanvasLocation, _scaleBounds, _owner.DiagramScaleMinimum, _owner.DiagramScaleMaximum);
                    return GH_ObjectResponse.Capture;
                }

                if (_textBounds.Contains(e.CanvasLocation))
                {
                    _draggingSlider = 2;
                    UpdateSlider(e.CanvasLocation, _textBounds, _owner.TextSizeMinimum, _owner.TextSizeMaximum);
                    return GH_ObjectResponse.Capture;
                }
            }

            return base.RespondToMouseDown(sender, e);
        }

        public override GH_ObjectResponse RespondToMouseMove(
            GH_Canvas sender,
            GH_CanvasMouseEvent e)
        {
            if (_draggingSlider == 1)
            {
                UpdateSlider(e.CanvasLocation, _scaleBounds, _owner.DiagramScaleMinimum, _owner.DiagramScaleMaximum);
                return GH_ObjectResponse.Handled;
            }

            if (_draggingSlider == 2)
            {
                UpdateSlider(e.CanvasLocation, _textBounds, _owner.TextSizeMinimum, _owner.TextSizeMaximum);
                return GH_ObjectResponse.Handled;
            }

            return base.RespondToMouseMove(sender, e);
        }

        public override GH_ObjectResponse RespondToMouseUp(
            GH_Canvas sender,
            GH_CanvasMouseEvent e)
        {
            if (_draggingSlider != 0)
            {
                _draggingSlider = 0;
                return GH_ObjectResponse.Release;
            }

            return base.RespondToMouseUp(sender, e);
        }

        public override GH_ObjectResponse RespondToMouseDoubleClick(
            GH_Canvas sender,
            GH_CanvasMouseEvent e)
        {
            if (e.Button == MouseButtons.Left && _scaleBounds.Contains(e.CanvasLocation))
            {
                _owner.EditDiagramScaleRange();
                return GH_ObjectResponse.Handled;
            }

            if (e.Button == MouseButtons.Left && _textBounds.Contains(e.CanvasLocation))
            {
                _owner.EditTextSizeRange();
                return GH_ObjectResponse.Handled;
            }

            return base.RespondToMouseDoubleClick(sender, e);
        }

        private void DrawSlider(
            Graphics graphics,
            RectangleF bounds,
            string label,
            double value,
            double minimum,
            double maximum,
            string format)
        {
            var labelBounds = bounds;
            labelBounds.Width = 78f;
            using (var textBrush = new SolidBrush(Color.White))
            using (var trackBrush = new SolidBrush(TrackColor))
            using (var fillBrush = new SolidBrush(FillColor))
            using (var valueBrush = new SolidBrush(Color.White))
            {
                graphics.DrawString(label, SystemFonts.MessageBoxFont, textBrush, labelBounds);

                var track = new RectangleF(
                    bounds.Left + 82f,
                    bounds.Top + 7f,
                    Math.Max(20f, bounds.Width - 126f),
                    4f);
                graphics.FillRectangle(trackBrush, track);
                var normalized = (float)((value - minimum) / (maximum - minimum));
                normalized = Math.Max(0f, Math.Min(1f, normalized));
                graphics.FillRectangle(fillBrush, track.Left, track.Top, track.Width * normalized, track.Height);
                var knobX = track.Left + track.Width * normalized;
                graphics.FillEllipse(fillBrush, knobX - 5f, track.Top - 4f, 10f, 12f);

                var valueText = value.ToString(format, CultureInfo.InvariantCulture);
                var valueBounds = bounds;
                valueBounds.X = bounds.Right - 40f;
                valueBounds.Width = 40f;
                using (var formatInfo = new StringFormat
                {
                    Alignment = StringAlignment.Far,
                    LineAlignment = StringAlignment.Center,
                })
                {
                    graphics.DrawString(valueText, SystemFonts.MessageBoxFont, valueBrush, valueBounds, formatInfo);
                }
            }
        }

        private void UpdateSlider(PointF location, RectangleF bounds, double minimum, double maximum)
        {
            var trackLeft = bounds.Left + 82f;
            var trackRight = bounds.Right - 44f;
            var normalized = (double)(location.X - trackLeft) / Math.Max(1f, trackRight - trackLeft);
            normalized = Math.Max(0.0, Math.Min(1.0, normalized));
            var value = minimum + (maximum - minimum) * normalized;

            if (_draggingSlider == 1)
            {
                _owner.SetDiagramScale(value);
            }
            else if (_draggingSlider == 2)
            {
                _owner.SetTextSize(value);
            }
        }
    }
}
