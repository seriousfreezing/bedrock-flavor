#version 330
#extension GL_ARB_separate_shader_objects : require

#include <minecraft:fog.glsl>
#include <minecraft:dynamictransforms.glsl>
#include <minecraft:oit.glsl>

uniform sampler2D Sampler0;

layout(location = 0) in float sphericalVertexDistance;
layout(location = 1) in float cylindricalVertexDistance;
layout(location = 2) in vec4 vertexColor;
layout(location = 3) in vec2 texCoord0;

#ifndef OIT_ALPHA_ONLY
layout(location = 0) out vec4 fragColor;
#endif

float sdPolygon(vec2 p, float s) {
    float angle = atan(p.y, p.x) + 3.14159265;
    float sectorAngle = 6.2831853 / s;
    float edgeDistance = cos(floor(0.5 + angle / sectorAngle) * sectorAngle - angle) * length(p);
    return edgeDistance - 1.0;
}

vec4 calculateFinalColor(vec4 color) {
    #ifdef OIT_ACCUMULATE
    color = sampleColorForAccumulation(color);
    vec4 fogColor = vec4(FogColor.rgb * color.a, FogColor.a);
    #else
    vec4 fogColor = FogColor;
    #endif
    return apply_fog(color, sphericalVertexDistance, cylindricalVertexDistance, FogEnvironmentalStart, FogEnvironmentalEnd, FogRenderDistanceStart, FogRenderDistanceEnd, fogColor);
}

void main() {
    vec2 uv = texCoord0 * 2.0 - 1.0;
    float shapeAlpha = step(sdPolygon(uv, 12.0), 0.0);

    vec4 tex = texture(Sampler0, clamp(texCoord0, 0.0, 1.0));
    
    vec4 color = vec4(tex.rgb, shapeAlpha);
    
    color *= vertexColor * ColorModulator;

    #ifdef OIT_ALPHA_ONLY
    executeAlphaOnlyPhase(gl_FragCoord.z, color.a);
    #else
    fragColor = calculateFinalColor(color);
    #endif
}