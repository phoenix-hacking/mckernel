#include <errno.h>
#include <stddef.h>
#include <unistd.h>

static int write_all(int fd, const unsigned char *bytes, size_t count)
{
    size_t done = 0;
    while (done < count) {
        ssize_t result = write(fd, bytes + done, count - done);
        if (result < 0 && errno == EINTR) {
            continue;
        }
        if (result <= 0) {
            return -1;
        }
        done += (size_t)result;
    }
    return 0;
}

int main(void)
{
    unsigned char out[256];
    unsigned char err[256];
    for (size_t i = 0; i < sizeof(out); ++i) {
        out[i] = (unsigned char)i;
        err[i] = (unsigned char)(255 - i);
    }
    for (unsigned int chunk = 0; chunk < 16; ++chunk) {
        if (write_all(STDOUT_FILENO, out, sizeof(out)) != 0 ||
            write_all(STDERR_FILENO, err, sizeof(err)) != 0) {
            return 41;
        }
    }
    return 0;
}
