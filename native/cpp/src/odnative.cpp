#include <cstdint>
#include <vector>
#include <algorithm>

extern "C" {

void od_adjust_rgb(uint8_t* data, int pixels, float brightness, float contrast, int grayscale) {
    if (data == nullptr || pixels <= 0) {
        return;
    }
    for (int index = 0; index < pixels; ++index) {
        const int base = index * 3;
        for (int channel = 0; channel < 3; ++channel) {
            float value = static_cast<float>(data[base + channel]) / 255.0f;
            value = (value - 0.5f) * contrast + 0.5f + brightness;
            if (value < 0.0f) value = 0.0f;
            if (value > 1.0f) value = 1.0f;
            data[base + channel] = static_cast<uint8_t>(value * 255.0f + 0.5f);
        }
        if (grayscale) {
            const uint8_t luma = static_cast<uint8_t>(
                0.299f * data[base] + 0.587f * data[base + 1] + 0.114f * data[base + 2] + 0.5f);
            data[base] = data[base + 1] = data[base + 2] = luma;
        }
    }
}

void od_smooth_stroke(float* xy, int count, int passes) {
    if (xy == nullptr || count < 3 || passes <= 0) {
        return;
    }
    std::vector<float> current(xy, xy + count * 2);
    std::vector<float> next(current.size());
    for (int pass = 0; pass < passes; ++pass) {
        next[0] = current[0];
        next[1] = current[1];
        for (int index = 1; index < count - 1; ++index) {
            next[index * 2] = (current[(index - 1) * 2] + current[index * 2] + current[(index + 1) * 2]) / 3.0f;
            next[index * 2 + 1] =
                (current[(index - 1) * 2 + 1] + current[index * 2 + 1] + current[(index + 1) * 2 + 1]) / 3.0f;
        }
        next[(count - 1) * 2] = current[(count - 1) * 2];
        next[(count - 1) * 2 + 1] = current[(count - 1) * 2 + 1];
        current.swap(next);
    }
    std::copy(current.begin(), current.end(), xy);
}

}
