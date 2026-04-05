// src/hal/linux/LinuxTransportFactory.cpp
// Linux transport factory implementation

#include "hal/linux/LinuxTransportFactory.h"

#if PLATFORM_LINUX

#include <cstdio>
#include <cstring>
#include <fcntl.h>
#include <unistd.h>
#include <termios.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <netdb.h>

namespace hal {

// Simple UART transport wrapper
struct LinuxUartTransport {
    int fd;
    char device[256];
};

// Simple TCP transport wrapper
struct LinuxTcpTransport {
    int fd;
    char host[256];
    uint16_t port;
};

void* LinuxTransportFactory::createUart(const UartTransportConfig& config) {
    // Device path is in the device field
    if (!config.device || config.device[0] == '\0') {
        return nullptr;
    }

    int fd = open(config.device, O_RDWR | O_NOCTTY | O_NONBLOCK);
    if (fd < 0) {
        return nullptr;
    }

    // Configure serial port
    struct termios tty;
    if (tcgetattr(fd, &tty) != 0) {
        close(fd);
        return nullptr;
    }

    // Set baud rate
    speed_t baud;
    switch (config.baudRate) {
        case 9600:   baud = B9600;   break;
        case 19200:  baud = B19200;  break;
        case 38400:  baud = B38400;  break;
        case 57600:  baud = B57600;  break;
        case 115200: baud = B115200; break;
        case 230400: baud = B230400; break;
        case 460800: baud = B460800; break;
        case 921600: baud = B921600; break;
        default:     baud = B115200; break;
    }
    cfsetispeed(&tty, baud);
    cfsetospeed(&tty, baud);

    // 8N1 configuration
    tty.c_cflag &= ~PARENB;  // No parity
    tty.c_cflag &= ~CSTOPB;  // 1 stop bit
    tty.c_cflag &= ~CSIZE;
    tty.c_cflag |= CS8;      // 8 data bits

    // Disable flow control
    tty.c_cflag &= ~CRTSCTS;
    tty.c_cflag |= CREAD | CLOCAL;

    // Raw mode
    tty.c_lflag &= ~(ICANON | ECHO | ECHOE | ISIG);
    tty.c_iflag &= ~(IXON | IXOFF | IXANY);
    tty.c_iflag &= ~(IGNBRK | BRKINT | PARMRK | ISTRIP | INLCR | IGNCR | ICRNL);
    tty.c_oflag &= ~OPOST;

    // Minimum bytes and timeout
    tty.c_cc[VMIN] = 0;
    tty.c_cc[VTIME] = 1;  // 100ms timeout

    if (tcsetattr(fd, TCSANOW, &tty) != 0) {
        close(fd);
        return nullptr;
    }

    // Flush any pending data
    tcflush(fd, TCIOFLUSH);

    auto* transport = new LinuxUartTransport();
    transport->fd = fd;
    strncpy(transport->device, config.device, sizeof(transport->device) - 1);
    transport->device[sizeof(transport->device) - 1] = '\0';

    return transport;
}

void* LinuxTransportFactory::createTcpClient(const char* host, uint16_t port) {
    if (!host || host[0] == '\0' || port == 0) {
        return nullptr;
    }

    // Resolve hostname
    struct hostent* server = gethostbyname(host);
    if (!server) {
        return nullptr;
    }

    // Create socket
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    if (fd < 0) {
        return nullptr;
    }

    // Connect
    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_port = htons(port);
    memcpy(&addr.sin_addr.s_addr, server->h_addr, server->h_length);

    if (connect(fd, (struct sockaddr*)&addr, sizeof(addr)) < 0) {
        close(fd);
        return nullptr;
    }

    auto* transport = new LinuxTcpTransport();
    transport->fd = fd;
    strncpy(transport->host, host, sizeof(transport->host) - 1);
    transport->host[sizeof(transport->host) - 1] = '\0';
    transport->port = port;

    return transport;
}

} // namespace hal

#endif // PLATFORM_LINUX
