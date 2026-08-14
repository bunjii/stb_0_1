using System;
using System.Drawing;
using System.Windows.Forms;
using Grasshopper.GUI;
using Grasshopper.GUI.Canvas;
using Grasshopper.Kernel;
using Grasshopper.Kernel.Attributes;

namespace StbGrasshopper
{
    /// <summary>
    /// Adds a section-type drop-down to the Section component body.
    /// </summary>
    internal sealed class StbSectionAttributes : GH_ComponentAttributes
    {
        private static readonly Color DropDownColor = Color.FromArgb(70, 76, 82);
        private readonly StbSectionComponent _owner;
        private RectangleF _dropDownBounds;

        public StbSectionAttributes(StbSectionComponent owner)
            : base(owner)
        {
            _owner = owner;
        }

        protected override void Layout()
        {
            base.Layout();

            const float stripHeight = 25f;
            const float margin = 4f;
            const float dropDownPadding = 34f;

            var original = Bounds;
            var longestTypeName = 0;
            for (var type = 0; type < StbSectionDimensions.TypeCount; type++)
            {
                longestTypeName = Math.Max(
                    longestTypeName,
                    GH_FontServer.StringWidth(
                        StbSectionDimensions.TypeName(type),
                        GH_FontServer.Standard));
            }

            // base.Layout() has already sized the component for the current
            // input/output labels. Only enlarge it when the drop-down needs
            // more room.
            var dropDownWidth = longestTypeName + dropDownPadding;
            var width = Math.Max(original.Width, dropDownWidth + margin * 2f);
            var left = original.X - (width - original.Width) * 0.5f;
            Bounds = new RectangleF(left, original.Y, width, original.Height + stripHeight);

            // Keep Grasshopper's standard label-to-socket spacing. Move each
            // complete parameter attribute to the new edge instead of asking
            // the layout helpers to expand the label regions outwards.
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

            _dropDownBounds = new RectangleF(
                Bounds.Left + margin,
                original.Bottom + 3f,
                Bounds.Width - margin * 2f,
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

            using (var fill = new SolidBrush(DropDownColor))
            using (var border = new Pen(Color.FromArgb(45, 50, 55), 1f))
            using (var textBrush = new SolidBrush(Color.White))
            using (var format = new StringFormat
            {
                Alignment = StringAlignment.Near,
                LineAlignment = StringAlignment.Center,
            })
            {
                graphics.FillRectangle(fill, _dropDownBounds);
                graphics.DrawRectangle(
                    border,
                    _dropDownBounds.X,
                    _dropDownBounds.Y,
                    _dropDownBounds.Width,
                    _dropDownBounds.Height);

                var textBounds = _dropDownBounds;
                textBounds.X += 6f;
                textBounds.Width -= 22f;
                graphics.DrawString(
                    _owner.SectionTypeName,
                    SystemFonts.MessageBoxFont,
                    textBrush,
                    textBounds,
                    format);

                var arrowX = _dropDownBounds.Right - 12f;
                var arrowY = _dropDownBounds.Top + _dropDownBounds.Height * 0.5f;
                graphics.FillPolygon(
                    textBrush,
                    new[]
                    {
                        new PointF(arrowX - 4f, arrowY - 2f),
                        new PointF(arrowX + 4f, arrowY - 2f),
                        new PointF(arrowX, arrowY + 3f),
                    });
            }
        }

        public override GH_ObjectResponse RespondToMouseDown(
            GH_Canvas sender,
            GH_CanvasMouseEvent e)
        {
            if (e.Button != MouseButtons.Left || !_dropDownBounds.Contains(e.CanvasLocation))
            {
                return base.RespondToMouseDown(sender, e);
            }

            var menu = new ContextMenuStrip();
            for (var type = 0; type < StbSectionDimensions.TypeCount; type++)
            {
                var item = new ToolStripMenuItem(StbSectionDimensions.TypeName(type))
                {
                    Checked = type == _owner.SectionType,
                    Tag = type,
                };
                menu.Items.Add(item);
            }

            menu.ItemClicked += (_, args) =>
            {
                if (args.ClickedItem.Tag is int selectedType)
                {
                    // Run after the native drop-down has closed. Modifying
                    // Grasshopper parameters during ToolStrip dispatch can be
                    // ignored or fail silently on some Rhino 8 builds.
                    sender.BeginInvoke(
                        new Action(() => _owner.SetSectionType(selectedType)));
                }
            };
            menu.Show(sender, e.ControlLocation);
            return GH_ObjectResponse.Handled;
        }
    }
}
