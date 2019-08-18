import math
import numpy as np
import moderngl

from ..color import convert_color
from ..allocators.vertlists import VAO
from .polygons import AbstractShape


#: Shader for a plain color fill
PLAIN_COLOR = dict(
    vertex_shader='''
        #version 330

        uniform mat4 proj;

        in vec2 in_vert;
        in vec4 in_color;
        out vec4 color;

        void main() {
            gl_Position = proj * vec4(in_vert, 0.0, 1.0);
            color = in_color;
        }
    ''',
    fragment_shader='''
        #version 330

        out vec4 f_color;
        in vec4 color;

        void main() {
            f_color = color;
        }
    ''',
)


WIDE_LINE = dict(
    vertex_shader='''
        #version 330

        in vec2 in_vert;
        in vec4 in_color;
        out vec4 g_color;
        out float width;

        void main() {
            gl_Position = vec4(in_vert, 0.0, 1.0);
            g_color = in_color;
        }
    ''',
    geometry_shader="""
#version 330 core
layout (lines_adjacency) in;
//layout (triangle_strip, max_vertices = 2) out;
layout (triangle_strip, max_vertices = 4) out;

in vec4 g_color[];
in float width[];
out vec4 color;

const float MITRE_LIMIT = 6.0;
const float WIDTH = 2.3;

vec2 rot90(vec2 v) {
    return vec2(-v.y, v.x);
}

uniform mat4 proj;


void mitre(vec2 a, vec2 b, vec2 c) {
    vec2 ab = normalize(b - a);
    vec2 bc = normalize(c - b);

    if (length(bc) < 1e-6) {
        bc = ab;
    }

    // across bc
    vec2 xbc = rot90(bc);

    vec2 along = normalize(ab + bc);
    vec2 across_mitre = rot90(along);

    float scale = 1.0 / dot(xbc, across_mitre);

    //This kind of works Ok although it does cause the width to change
    // scale = min(scale, MITRE_LIMIT);  // limit extension of the mitre
    vec2 across = WIDTH * across_mitre * scale;

    gl_Position = proj * vec4(b + across, 0.0, 1.0);
    EmitVertex();

    gl_Position = proj * vec4(b - across, 0.0, 1.0);
    EmitVertex();
}


void main() {
    color = g_color[1];

    vec2 a = gl_in[0].gl_Position.xy;
    vec2 b = gl_in[1].gl_Position.xy;
    vec2 c = gl_in[2].gl_Position.xy;
    vec2 d = gl_in[3].gl_Position.xy;

    mitre(a, b, c);
    mitre(b, c, d);

    EndPrimitive();
}
""",
    fragment_shader='''
        #version 330

        out vec4 f_color;
        in vec4 color;

        void main() {
            f_color = color;
        }
    ''',
)


def color_vao(
        mode: int,
        ctx: moderngl.Context,
        shadermgr: 'wasabi2d.layers.ShaderManager') -> VAO:
    """Build a BAO for rendering plain colored objects."""
    return VAO(
        mode=mode,
        ctx=ctx,
        prog=shadermgr.get(**PLAIN_COLOR),
        dtype=np.dtype([
            ('in_vert', '2f4'),
            ('in_color', '4f4'),
        ])
    )


def line_vao(
        ctx: moderngl.Context,
        shadermgr: 'wasabi2d.layers.ShaderManager') -> VAO:
    """Build a VAO for rendering lines."""
    return VAO(
        mode=moderngl.LINE_STRIP_ADJACENCY,
        ctx=ctx,
        prog=shadermgr.get(**WIDE_LINE),
        dtype=np.dtype([
            ('in_vert', '2f4'),
            ('in_color', '4f4'),
        ])
    )


def shape_vao(
        ctx: moderngl.Context,
        shadermgr: 'wasabi2d.layers.ShaderManager') -> VAO:
    """Build a VAO for rendering shapes."""
    return color_vao(
        mode=moderngl.TRIANGLES,
        ctx=ctx,
        shadermgr=shadermgr,
    )


class Circle(AbstractShape):
    """A circle drawn with lines."""

    __slots__ = (
        'layer', 'segments',
        '_radius',
        'orig_verts',
    )

    def __init__(
            self,
            layer,
            pos=(0, 0),
            radius=100,
            color=(1, 1, 1, 1),
            segments=None):
        super().__init__()
        self.layer = layer
        self.segments = segments or max(4, round(math.pi * radius))
        self.pos = pos
        self._radius = radius

        theta = np.linspace(0, 2 * np.pi, self.segments)
        self.orig_verts = np.vstack([
            radius * np.cos(theta),
            radius * np.sin(theta),
            np.ones(self.segments)
        ]).T.astype('f4')

        # There's a duplicate vertex so move the first vertex to the center
        self.orig_verts[0][:2] = 0

        self._color = convert_color(color)
        self._set_dirty()

    def _stroke_indices(self):
        """Indexes for drawing the stroke as a LINE_STRIP."""
        n = self.segments
        return np.array(
            [n - 1, *range(1, n), 1, 2],
            dtype='i4'
        )

    def _fill_indices(self):
        """Indexes for drawing the fill as TRIANGLES."""
        idxs = np.array([
            (0, i, i + 1)
            for i in range(1, self.segments)
        ], dtype='i4')
        idxs[-1][2] = 1
        return idxs.reshape((-1))

    @property
    def left(self):
        return self.pos[0] - self._radius

    @left.setter
    def left(self, v):
        self.pos[0] = v + self._radius
        self._set_dirty()

    @property
    def right(self):
        return self.pos[0] + self._radius

    @right.setter
    def right(self, v):
        self.pos[0] = v - self._radius
        self._set_dirty()

    @property
    def top(self):
        return self.pos[1] - self._radius

    @top.setter
    def top(self, v):
        self.pos[1] = v + self._radius
        self._set_dirty()

    @property
    def bottom(self):
        return self.pos[1] + self._radius

    @bottom.setter
    def bottom(self, v):
        self.pos[1] = v - self._radius
        self._set_dirty()

    def colliderect(self, ano):
        return not (
            self.left > ano.right
            or self.right < ano.left
            or self.top > ano.bottom
            or self.bottom < ano.top
        )

    def collidelist(self, lst):
        for idx, o in enumerate(lst):
            if self.colliderect(o):
                return idx
        return -1

    @property
    def centerx(self):
        return self.pos[0]

    @property
    def centery(self):
        return self.pos[1]