using System;
using System.Drawing;
using System.Drawing.Drawing2D;

namespace StbGrasshopper
{
    internal static class StbIcons
    {
        public static Bitmap Analyze => Lazy(ref _analyze, Color.FromArgb(46, 125, 180), DrawPlay);
        public static Bitmap Displacements => Lazy(ref _displacements, Color.FromArgb(40, 150, 120), DrawArrow);
        public static Bitmap Forces => Lazy(ref _forces, Color.FromArgb(180, 90, 50), DrawForce);
        public static Bitmap DeformedShape => Lazy(ref _deformedShape, Color.FromArgb(120, 70, 160), DrawDeformed);
        public static Bitmap Node => Lazy(ref _node, Color.FromArgb(70, 130, 180), DrawDot);
        public static Bitmap DatNodes => Lazy(ref _datNodes, Color.FromArgb(55, 110, 165), (g, pen, brush) => { DrawDot(g, pen, brush); DrawFile(g, pen, brush); });
        public static Bitmap DatBeams => Lazy(ref _datBeams, Color.FromArgb(55, 110, 165), (g, pen, brush) => { DrawBeam(g, pen, brush); DrawFile(g, pen, brush); });
        public static Bitmap Beam => Lazy(ref _beam, Color.FromArgb(90, 90, 90), DrawBeam);
        public static Bitmap Material => Lazy(ref _material, Color.FromArgb(130, 130, 130), DrawBlock);
        public static Bitmap Section => Lazy(ref _section, Color.FromArgb(110, 110, 110), DrawSection);
        public static Bitmap Support => Lazy(ref _support, Color.FromArgb(160, 120, 60), DrawSupport);
        public static Bitmap Load => Lazy(ref _load, Color.FromArgb(190, 70, 70), DrawLoad);
        public static Bitmap Assemble => Lazy(ref _assemble, Color.FromArgb(80, 120, 90), DrawStack);
        public static Bitmap LoadCases => Lazy(ref _loadCases, Color.FromArgb(70, 110, 150), DrawLoadCases);

        private static Bitmap _analyze;
        private static Bitmap _displacements;
        private static Bitmap _forces;
        private static Bitmap _deformedShape;
        private static Bitmap _node;
        private static Bitmap _datNodes;
        private static Bitmap _datBeams;
        private static Bitmap _beam;
        private static Bitmap _material;
        private static Bitmap _section;
        private static Bitmap _support;
        private static Bitmap _load;
        private static Bitmap _assemble;
        private static Bitmap _loadCases;

        private static Bitmap Lazy(ref Bitmap cache, Color back, Action<Graphics, Pen, SolidBrush> draw)
        {
            if (cache != null)
            {
                return cache;
            }

            var bmp = new Bitmap(24, 24);
            using (var g = Graphics.FromImage(bmp))
            {
                g.SmoothingMode = SmoothingMode.AntiAlias;
                g.Clear(back);
                using (var pen = new Pen(Color.White, 2f))
                using (var brush = new SolidBrush(Color.White))
                {
                    draw(g, pen, brush);
                }
            }

            cache = bmp;
            return cache;
        }

        private static void DrawPlay(Graphics g, Pen pen, SolidBrush brush)
        {
            g.FillPolygon(brush, new[] { new Point(8, 6), new Point(8, 18), new Point(18, 12) });
        }

        private static void DrawArrow(Graphics g, Pen pen, SolidBrush brush)
        {
            g.DrawLine(pen, 4, 14, 16, 14);
            g.DrawLine(pen, 12, 8, 16, 14);
            g.DrawLine(pen, 12, 20, 16, 14);
        }

        private static void DrawForce(Graphics g, Pen pen, SolidBrush brush)
        {
            g.DrawLine(pen, 6, 18, 18, 6);
            g.DrawLine(pen, 14, 6, 18, 6);
            g.DrawLine(pen, 18, 6, 18, 10);
            g.DrawString("F", new Font("Arial", 8f, FontStyle.Bold), brush, 4f, 10f);
        }

        private static void DrawDeformed(Graphics g, Pen pen, SolidBrush brush)
        {
            g.DrawLine(pen, 4, 16, 10, 16);
            g.DrawBezier(pen, 10, 16, 13, 8, 16, 8, 20, 10);
            g.FillEllipse(brush, 18, 8, 4, 4);
        }

        private static void DrawDot(Graphics g, Pen pen, SolidBrush brush)
        {
            g.FillEllipse(brush, 9, 9, 6, 6);
        }

        private static void DrawBeam(Graphics g, Pen pen, SolidBrush brush)
        {
            g.DrawLine(pen, 5, 17, 19, 7);
            g.FillEllipse(brush, 3, 15, 4, 4);
            g.FillEllipse(brush, 17, 5, 4, 4);
        }

        private static void DrawFile(Graphics g, Pen pen, SolidBrush brush)
        {
            g.DrawRectangle(pen, 14, 14, 7, 7);
            g.DrawLine(pen, 14, 16, 19, 16);
        }

        private static void DrawBlock(Graphics g, Pen pen, SolidBrush brush)
        {
            g.FillRectangle(brush, 6, 8, 12, 10);
        }

        private static void DrawSection(Graphics g, Pen pen, SolidBrush brush)
        {
            g.DrawRectangle(pen, 7, 7, 10, 10);
            g.DrawLine(pen, 7, 12, 17, 12);
            g.DrawLine(pen, 12, 7, 12, 17);
        }

        private static void DrawSupport(Graphics g, Pen pen, SolidBrush brush)
        {
            g.DrawLine(pen, 12, 6, 12, 14);
            g.DrawLine(pen, 6, 14, 18, 14);
            for (var x = 7; x <= 16; x += 3)
            {
                g.DrawLine(pen, x, 14, x - 2, 18);
            }
        }

        private static void DrawLoad(Graphics g, Pen pen, SolidBrush brush)
        {
            g.DrawLine(pen, 12, 5, 12, 15);
            g.DrawLine(pen, 8, 11, 12, 15);
            g.DrawLine(pen, 16, 11, 12, 15);
        }

        private static void DrawStack(Graphics g, Pen pen, SolidBrush brush)
        {
            g.DrawRectangle(pen, 5, 5, 14, 4);
            g.DrawRectangle(pen, 5, 10, 14, 4);
            g.DrawRectangle(pen, 5, 15, 14, 4);
        }

        private static void DrawLoadCases(Graphics g, Pen pen, SolidBrush brush)
        {
            g.DrawString("0", new Font("Arial", 7f, FontStyle.Bold), brush, 4f, 4f);
            g.DrawString("1", new Font("Arial", 7f, FontStyle.Bold), brush, 11f, 9f);
            g.DrawString("2", new Font("Arial", 7f, FontStyle.Bold), brush, 6f, 14f);
        }
    }
}
