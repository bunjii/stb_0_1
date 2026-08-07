using System;
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

            const float minimumWidth = 150f;
            const float stripHeight = 23f;
            const float margin = 4f;
            const float gap = 2f;

            var original = Bounds;
            var width = Math.Max(original.Width, minimumWidth);
            var left = original.X - (width - original.Width) * 0.5f;

            Bounds = new RectangleF(left, original.Y, width, original.Height + stripHeight);

            if (_owner.Params.Input.Count > 0 && _owner.Params.Input[0].Attributes != null)
            {
                var pivot = _owner.Params.Input[0].Attributes.Pivot;
                _owner.Params.Input[0].Attributes.Pivot = new PointF(Bounds.Left, pivot.Y);
            }

            if (_owner.Params.Output.Count > 0 && _owner.Params.Output[0].Attributes != null)
            {
                var pivot = _owner.Params.Output[0].Attributes.Pivot;
                _owner.Params.Output[0].Attributes.Pivot = new PointF(Bounds.Right, pivot.Y);
            }

            var availableWidth = Bounds.Width - margin * 2f - gap * (Labels.Length - 1);
            var buttonWidth = availableWidth / Labels.Length;
            var buttonY = original.Bottom + 3f;

            for (var i = 0; i < _buttons.Length; i++)
            {
                _buttons[i] = new RectangleF(
                    Bounds.Left + margin + i * (buttonWidth + gap),
                    buttonY,
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
