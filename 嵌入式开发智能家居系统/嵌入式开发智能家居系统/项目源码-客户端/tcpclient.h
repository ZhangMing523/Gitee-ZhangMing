#ifndef TCPCLIENT_H
#define TCPCLIENT_H

#include <QWidget>
#include <QTcpSocket> //1.头文件
#include <QTimer>
#include <QNetworkAccessManager>
#include <QNetworkReply>//HTTP协议的类

QT_BEGIN_NAMESPACE
namespace Ui { class Tcpclient; }
QT_END_NAMESPACE

class Tcpclient : public QWidget
{
    Q_OBJECT

public:
    Tcpclient(QWidget *parent = nullptr);
    ~Tcpclient();

private slots:
    void on_pushButtonconnect_clicked();
    void my_connected();
      void my_disconnected();
      void on_pushButton_ledon_clicked();


      void recv_data();
      void picture_data();

      void on_pushButtonstart_clicked();

      void my_time();

      void on_pushButton_led_off_clicked();

      void on_pushButton_buzzer_on_clicked();

      void on_pushButton_buzzer_off_clicked();

      void on_pushButton_fan_on_clicked();

      void on_pushButton_fan_off_clicked();

      void on_pushButton_fan_low_clicked();

      void on_pushButton_fan_mid_clicked();

      void on_pushButton_fan_high_clicked();

      void on_pushButton_nixie_tube_on_clicked();

      void on_pushButton_nixie_tube_off_clicked();

      void on_label_pic_linkActivated(const QString &link);

      void on_label_light_linkActivated(const QString &link);

      void on_pushButton_get_clicked();
      //deepseek
      void onNetworkReplyFinished(QNetworkReply *reply);
      void onReadyRead();  // 这是槽函数声明
      void on_pushButton_ai_clicked();

private:
    Ui::Tcpclient *ui;
    QTcpSocket *socket;
    QTcpSocket *socketd;
    QTimer * T;
    QNetworkAccessManager *httphelper;
    unsigned int pic_len;
    unsigned char buf[1024*100];  //2M
    int pic_flag;
};
#endif // TCPCLIENT_H
