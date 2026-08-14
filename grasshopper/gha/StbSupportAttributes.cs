using System.Drawing;
using Grasshopper.GUI;
using Grasshopper.GUI.Canvas;
using Grasshopper.Kernel.Attributes;

namespace StbGrasshopper
{
    /// <summary>
    /// Adds six independent restraint toggles to the Support component body.
    /// Blue means restrained; grey means free.
    /// </summary>
    internal sealed class StbSupportAttributes : GH_ComponentAttributes
    {
        private static readonly string[] Labels = { "Tx", "Ty", "Tz", "Rx", "Ry", "Rz" };
        private static readonly Color ActiveColor = Color.FromArgb(0, 174, 227);
        private static readonly Color InactiveColor = Color.FromArgb(110, 116, 122);

        private readonly StbSupportComponent _owner;
        private readonly RectangleF[] _buttons = new RectangleF[Labels.Length];

        public StbSupportAttributes(StbSupportComponent owner)
            : base(owner)
        {
            _owner = owner;
        }

        protected override void Layout()
        {
            base.Layout();

            const int columnCount = 3;
            const float stripHeight = 42f;
            const float margin = 4f;
            const float gap = 2f;

            var original = Bounds;
            Bounds = new RectangleF(
                original.X,
                original.Y,
                original.Width,
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

            var availableWidth = Bounds.Width - margin * 2f - gap * (columnCount - 1);
            var buttonWidth = availableWidth / columnCount;

            for (var i = 0; i < _buttons.Length; i++)
            {
                var row = i / columnCount;
                var column = i % columnCount;
                _buttons[i] = new RectangleF(
                    Bounds.Left + margin + column * (buttonWidth + gap),
                    original.Bottom + 3f + row * (17f + gap),
                    buttonWidth,
                    17f);
            }
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

            using (var border = new Pen(Color.FromArgb(75, 80, 85), 1f))
            using (var textBrush = new SolidBrush(Color.White))
            using (var format = new StringFormat
            {
                Alignment = StringAlignment.Center,
                LineAlignment = StringAlignment.Center,
            })
            {
                for (var i = 0; i < _buttons.Length; i++)
                {
                    using (var fill = new SolidBrush(
                        _owner.IsRestrained(i) ? ActiveColor : InactiveColor))
                    {
                        graphics.FillRectangle(fill, _buttons[i]);
                    }

                    graphics.DrawRectangle(
                        border,
                        _buttons[i].X,
                        _buttons[i].Y,
                        _buttons[i].Width,
                        _buttons[i].Height);
                    graphics.DrawString(
                        Labels[i],
                        SystemFonts.MessageBoxFont,
                        textBrush,
                        _buttons[i],
                        format);
                }
            }
        }

        public override GH_ObjectResponse RespondToMouseDown(
            GH_Canvas sender,
            GH_CanvasMouseEvent e)
        {
            for (var i = 0; i < _buttons.Length; i++)
            {
                if (_buttons[i].Contains(e.CanvasLocation))
                {
                    _owner.ToggleRestraint(i);
                    return GH_ObjectResponse.Handled;
                }
            }

            return base.RespondToMouseDown(sender, e);
        }
    }
}
